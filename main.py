import Node
import datetime
import sys

NODE: Node.Node = None

def print_options():
    op = """
join       <peer_mac_id> <port>
send       <peer_mac_id> <msg>
broadcast  <msg>
leave      <peer_mac_id>
info
rt
exit                               
        """
    print(op)


def arguments_handler():
    time = datetime.datetime.now().strftime("%H:%M:%S")
    print_options()
    try:
        args = input(f'[{time}] Waiting for command: ').strip().split()
        if not args:
            return
        cmd = args[0].lower()

        match cmd:
            case 'broadcast':
                if len(args) < 2:
                    print("[ERROR] Usage: broadcast <mensaje>")
                else:
                    NODE.broadcast(msg=' '.join(args[1:]))

            case 'send':
                if len(args) < 3:
                    print("[ERROR] Usage: send <peer_id> <mensaje>")
                else:
                    NODE.send(dest=args[1], msg=' '.join(args[2:]))

            case 'join':
                # if len(args) < 4:
                if len(args) < 3:
                    # print("[ERROR] Usage: join <peer_id> <ip_address> <port>")
                    print("[ERROR] Usage: join <peer_id> <port>")
                else:
                    #NODE.join(kid=' '.join(args[1:]))
                    # NODE.join(kid=args[1], ip_address=args[2], port=int(args[3]))
                    NODE.join(kid=args[1], port=int(args[2]))
                    

            case 'leave':
                if len(args) < 2:
                    print("[ERROR] Usage: leave <peer_id>")
                else:
                    NODE.leave(kid=' '.join(args[1]))

            case 'info':
                NODE.print_node_info()

            case 'rt':
                NODE.print_routing_table()

            case 'exit':
                print("[INFO] Exiting program...")
                NODE.server.close_server()
                sys.exit(0)
            case _:
                print(f'[{time}] Argument not defined')

    except Exception as e:
        print(f'[ERROR] Command error: {e}')


def main():
    global NODE
    time = datetime.datetime.now().strftime("%H:%M:%S")

    if NODE is None:
        name = input(f"[{time}] Enter the name of the node: ")
        NODE = Node.Node(name)
        print(f'{time}Hello: {NODE.get_name()}')
        
    while True:
        arguments_handler()


if __name__ == "__main__":
    main()
