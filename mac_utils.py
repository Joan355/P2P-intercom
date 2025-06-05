import json
import random

_ALPHA_NUMERIC = [str(x) for x in range(10)] + [chr(x) for x in range(ord('A'), ord('F') + 1)]


def get_umac(name: str) -> None:
    LOCAL_MAC = None
    with open(r"D:\python\libro\just_practicing\peer2peer\MAC_addrs_file.json", "r+") as file: 
        addrs: dict[any, any] = json.load(file)
        if name in addrs: 
            
            return addrs[name]
        file.seek(0)
        while (MAC := generate_mac()) in addrs.values():
            continue
        addrs[name] = MAC
        json.dump(addrs, file)
    LOCAL_MAC = MAC
    return LOCAL_MAC
    
            
def is_mac_direction(mac: str = None):
    import re
    if not mac: 
        return False
    
    regex = ("^([0-9A-Fa-f]{2}(:)){3}([0-9A-Fa-f]{2})$")
    
    p = re.compile(regex)
    return re.search(p, mac) is not None

def generate_mac() -> str:
    return f"{get_rchar()}{get_rchar()}:{get_rchar()}{get_rchar()}:{get_rchar()}{get_rchar()}:{get_rchar()}{get_rchar()}"

def get_rchar() -> str:
    return random.choice(_ALPHA_NUMERIC)


if __name__ == "__main__":
    mac = "01:23:89:AB"
    print(is_mac_direction(mac))