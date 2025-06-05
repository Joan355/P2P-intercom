import json


def deserialize(json_info: str) -> dict[str, str | int]: 
    """
    loads a string that contains json and converts it into a python object
    return: a python object
    """
    return json.loads(json_info)

def serialize(obj: any) -> str:
    """
    dumps a python object into a string
    return:  JSON formatted string
    """

    return json.dumps(obj)