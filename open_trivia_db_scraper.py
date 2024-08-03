import html
import json
import time
import warnings
from typing import Final, Sequence, TypeVar

from requests import Session
from tqdm import tqdm

ERROR_CODES: Final[dict[int, str]] = {
    0: "Success: Returned results successfully.",
    1: "No Results: Could not return results. The API doesn't have enough questions for your query. (Ex. Asking for "
       "50 Questions in a Category that only has 20.)",
    2: "Invalid Parameter: Contains an invalid parameter. Arguments passed in aren't valid. (Ex. Amount = Five)",
    3: "Token Not Found: Session Token does not exist.",
    4: "Token Empty: Session Token has returned all possible questions for the specified query. Resetting the Token "
       "is necessary.",
    5: "Rate Limit: Too many requests have occurred. Each IP can only access the API once every 5 seconds.",
}

StrDictSequence = TypeVar('StrDictSequence', str, dict, Sequence)


def unescape_any(obj: StrDictSequence) -> StrDictSequence:
    """
    Replace html-safe chars.
    :param obj: str | dict | Sequence
    :return:
    """
    if isinstance(obj, dict):
        escaped = {}
        for k, v in tqdm(obj.items()):
            escaped[html.unescape(k)] = unescape_any(v)
        return escaped
    if isinstance(obj, str):
        return html.unescape(obj)
    if isinstance(obj, Sequence):
        return type(obj)(unescape_any(el) for el in obj)

    warnings.warn(f'str, dict, Sequence expected, not {type(obj)}')
    return obj


def get_new_token(session: Session) -> str:
    response = session.get("https://opentdb.com/api_token.php?command=request")
    response.raise_for_status()  # Raise an error if the request failed
    return response.json()["token"]


def fetch_trivia_questions(session: Session, token: str) -> dict:
    """
    Return 50 questions from opentdb.com and unescape them.
    :param session: requests session
    :param token: obtainable with get_new_token
    :return: dict
    """
    response = session.get(f'https://opentdb.com/api.php?amount=50&token={token}')
    response.raise_for_status()  # Raise an error if the request failed
    json_data = response.json()
    if json_data["response_code"] != 0:
        raise Exception(ERROR_CODES.get(json_data["error"], "Unknown Error"))
    return unescape_any(json_data['results'])


def read_db() -> dict:
    """
    Load dict from db.json in same folder. If not found, return empty dict.
    :return: dict
    """
    try:
        with open('db.json') as f:
            db = json.loads(f.read())
            print(f"Loaded {len(db)} questions.")
        return db
    except (FileNotFoundError, json.decoder.JSONDecodeError) as error:
        print(error)
        return {}


def main():
    """
    Load db.json if present, fetch question from opentdb.com and save to db.json and db.csv.
    :return:
    """
    db = read_db()
    with Session() as session:
        token = get_new_token(session)

        try:
            while True:
                results = fetch_trivia_questions(session, token)
                for result in results:
                    db[result['question']] = result

                with open('db.json', 'w') as f:
                    json.dump(db, f)

                try:
                    import pandas as pd
                    df = pd.read_csv(db.values())
                    df.to_csv("db.csv", index=False)
                except ImportError:
                    print("pandas not installed, no csv will be saved.")

                # Show progress
                tqdm.write(f"Fetched {len(results)} questions. Total: {len(db)} questions saved.")
                time.sleep(5.5)

        except (KeyboardInterrupt, Exception) as e:
            print(e)
            with open('db.json', 'w') as f:
                json.dump(db, f, indent=4)
            print("Data saved. Exiting.")


#%%
if __name__ == '__main__':
    main()
