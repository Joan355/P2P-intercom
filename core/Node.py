from mac_utils import *
from json_utils import *
from copy import deepcopy
import time
import threading
import socket
import hashlib

MAX_HOP = 10
# BROADCAST, UNICAST, = 0, 1
BROADCAST, UNICAST = 0, 1

# Plantilla base para los mensajes
MESSAGE: dict[str, object] = {
    'id'       : -1,
    "type"     : -1,    # UNO DE {BROADCAST, UNICAST}
    "origin"   : "",
    "destine"  : "",
    "previous" : [],    # Lista: [MAC_del_nodo_que_reenvió, ip, port]
    "payload"  : "",
    "hop_count": 0
}


class Node:
    def __init__(self, name: str, daemon: bool = True) -> None:
        self._NAME: str = name
        self._LOCAL_MAC: str = self._NAME #cambiar cuando se hayan hecho las pruebas
        # self._LOCAL_MAC: str = get_umac(name)

        # ROUTING_TABLE:
        #   { destino_mac: {
        #         'next_hop': {
        #               'node'   : str, 
        #               'address': [ip,port]
        #         },
        #         'hop_count': int
        #     }
        #   }
        self._ROUTING_TABLE: dict[str, dict[str, object]] = {}

        # K_PEERS: { peer_mac: [ip, port] }
        self._K_PEERS: dict[str, list[object]] = {}
        self._SERVER: NodeServer = NodeServer(node=self, daemon=daemon)
        self._SERVER.init_server()
        self._M_REGISTER: list[str] = [] #debe mantener un limite de 10 registros

    def get_mac(self) -> str:
        return self._LOCAL_MAC

    def get_name(self) -> str:
        return self._NAME

    def get_peers(self) -> str:
        return str(self._K_PEERS)

    def print_routing_table(self) -> str:
        for k in self._ROUTING_TABLE.keys():
            print(\
f"""
[

    destine  : {k}
    next_hop : [
        node    : {self._ROUTING_TABLE[k]['next_hop']['node']}
        address : {self._ROUTING_TABLE[k]['next_hop']['address']} 
    ]
    hop_count: {self._ROUTING_TABLE[k]['hop_count']}

]
"""              )

    def get_server(self) -> "NodeServer":
        return self._SERVER

    def get_message(
        self,
        *,
        type: int,
        origin: str,
        destine: str,
        previous: list[object],
        payload: str,
        hop_count: int
    ) -> dict[str, object]:
        message: dict[str, object] = deepcopy(MESSAGE)
        message["id"] = self.generate_unic_id(origin=origin, destine=destine, payload=payload)
        message["type"]     = type
        message["origin"]   = origin
        message["destine"]  = destine
        message["previous"] = previous
        message["payload"]  = payload
        message["hop_count"] = hop_count
        return message

    def generate_unic_id(self, *, origin: str, destine: str, payload: str) -> str:
        data = [origin, destine, payload, str(time.time_ns())]
        random.shuffle(data)
        buffer = ':'.join(data)
        hash_obj = hashlib.sha256(buffer.encode())
        return hash_obj.hexdigest()

    def print_node_info(self) -> None:

        info = \
f"""
[
    name         : {self._NAME}
    MAC          : {self._LOCAL_MAC}
    local_address: {self._SERVER.get_address()}
    k_peers      : [
"""          
        for k,v in self._K_PEERS.items():
            info += \
f"""
                    {k}:{v}
"""
        info += """
                    ]
]
"""       
        print(info)
        

    #----------------------- Métodos principales -------------------------#
    def register_trace(
        self,
        *,
        destine: str,
        node: str,
        address: list[object],
        hop_count: int
    ) -> None:
        """
        Agrega o actualiza la entrada de 'destine' en la tabla de enrutamiento.
        """
        if destine not in self._ROUTING_TABLE or hop_count < self._ROUTING_TABLE[destine]["hop_count"]:
            self._ROUTING_TABLE[destine] = {
                "next_hop": {
                    "node": node,
                    "address": address
                },
                "hop_count": hop_count
            }


    def join(self, *, kid: str, ip_address: str = '127.0.0.1', port: int) -> None:
        """
        Agrega a K_PEERS si 'kid' es una MAC válida y aún no existe.
        """
        # if is_mac_direction(kid): # validacion e implementacion comentados por razones de simplicidad
        #     if kid not in self._K_PEERS:
        #         self._K_PEERS[kid] = [ip_address, port]
        #         print(f"[NODE] {kid} fue agregado a la lista de peers.")
        #     else:
        #         print(f"[NODE] {kid} ya estaba en la lista de peers.")
        # else:
        #     print(f"[NODE] {kid} no es una MAC válida; no se agregó.")


        if kid not in self._K_PEERS:
            self._K_PEERS[kid] = [ip_address, int(port)]
            print(f"[NODE] {kid} fue agregado a la lista de peers.")
        else: 
            print(f"[NODE] {kid} ya estaba en la lista de peers.")

    def leave(self, *, kid: str) -> None:
        """
        Elimina de K_PEERS si existe.
        """
        # if is_mac_direction(kid): # validacion e implementacion comentados por razones de simplicidad
        #     if kid in self._K_PEERS:
        #         del self._K_PEERS[kid]
        #         print(f"[NODE] {kid} fue removido de la lista de peers.")
        #     else:
        #         print(f"[NODE] {kid} no existía en la lista de peers.")
        # else:
        #     print(f"[NODE] {kid} no es una MAC válida; no se pudo remover.")

        if kid in self._K_PEERS:
            del self._K_PEERS[kid]
            print(f"[NODE] {kid} was removed from list of peers")
        else:
            print(f"[NODE] {kid} dit not exist in list of peers.")


    def send(
        self,
        *,
        dest: str = None,
        msg: str = None,
        data: dict[str, object] = None
    ) -> None:
        
        message = data or self.get_message(
            type=UNICAST,
            origin=self._LOCAL_MAC,
            destine=dest,
            previous=[self._LOCAL_MAC, *self._SERVER.get_address()],
            payload=msg,
            hop_count=0
        )
        
        destine = message['destine']


        if destine in self._K_PEERS:
            #print('[NODE] destine found in known peers  :  redirecting data...')
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.sendto(serialize(message).encode(), tuple(self._K_PEERS[destine]))
        elif destine in self._ROUTING_TABLE:
            #print('[NODE] destine found in routing table: redirecting data...')
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.sendto(serialize(message).encode(), tuple(self._ROUTING_TABLE[destine]['next_hop']['address']))
        else: 
            #print('[NODE] destine not found neither known peers nor routing table: sending broadcast...')
            if message['type'] != BROADCAST:
                message['type'] = BROADCAST
            self.broadcast(msg=message)

    def broadcast(
        self,
        *,
        msg: object | dict[str, object] = None
    ) -> None:
        
        message = msg if isinstance(msg, dict) else self.get_message(
            type=BROADCAST,
            origin=self._LOCAL_MAC,
            destine='',
            previous=[self._LOCAL_MAC, *self._SERVER.get_address()],
            payload=msg,
            hop_count=0
        )

        prev_name = message['previous'][0] # previous-node name

        if self._K_PEERS:

            for k_peer, dirr in self._K_PEERS.items():

                if not prev_name == k_peer:

                    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                        s.sendto(serialize(message).encode(), tuple(dirr))

        elif self._ROUTING_TABLE:

            for _, values in self._ROUTING_TABLE.items():

                if not prev_name == values['next_hop']['node']:

                    addrss = values['next_hop']['address']
                    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                        s.sendto(serialize(message).encode(), tuple(addrss))


    #-----------------------------------------------------------------# 

    def on_recv(self, message: str) -> None:
        
        try:
            data = deserialize(message)
        except Exception as e:
            print(f"[on_recv] Error upon deserializing: {e}")
            return
        
        data['hop_count'] += 1 # hop_count incremented in one

        message_id   = data['id']
        origin       = data['origin']
        destine      = data['destine']
        message_type = data['type']
        hop_count    = data['hop_count']
        prev_name    = data['previous'][0]
        prev_addrs   = data['previous'][1:]

        if hop_count > MAX_HOP or message_id in self._M_REGISTER:
            return

        
        if origin not in self._ROUTING_TABLE:
            self.register_trace(
                destine=origin,
                node=prev_name,
                address=prev_addrs,
                hop_count=hop_count
            )

        if destine == self._LOCAL_MAC: 

            self.print_message(data) #print data
            if message_type == BROADCAST: # reply with a message if message is BROADCAST type
                new_message = self.get_message(
                    type=UNICAST, 
                    origin=self._LOCAL_MAC,
                    destine=origin,
                    previous=[self._LOCAL_MAC, *self._SERVER.get_address()],
                    payload='path found',
                    hop_count=0
                )
                self.send(data=new_message) 

        else: 
            if destine == '':
                self.print_message(data)
            if len(self._M_REGISTER) >= 10: # if message register is full, pop firts item
                    self._M_REGISTER.pop(0)

            data['previous'] = [self._LOCAL_MAC, *self._SERVER.get_address()] # update previous with current position
            self._M_REGISTER.append(message_id)            
            self.send(data=data)



    def print_message(self, msg: dict[str, object]) -> None:

        message_string = f"""
        {'received from':>30}: {msg.get('origin', '')}
        {'message':>30}: {msg.get('payload', '')}
        {'hops':>30}: {msg.get('hop_count', 0)}
        """
        print(message_string)




class NodeServer:
    def __init__(
        self,
        *,
        node: Node,
        daemon: bool = True,
        ip_address: str = "127.0.0.1",
        port: int = 5050
    ) -> None:
        self._NODE = node
        self._ADDRESS = ip_address
        self._PORT = port
        self._server_state = True
        self._DAEMON = daemon

    def get_address(self) -> list[str | int]:
        return [self._ADDRESS, self._PORT]

    def _run_server(self, port: int) -> None:
        """
        Ejecuta un socket UDP que recibe paquetes y llama a node.on_recv().
        """
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                port_asignado = self.set_port(port)
                s.bind((self._ADDRESS, port_asignado))
                print(f"\n[SERVER] Node {self._NODE.get_name()} listening on {self._ADDRESS}:{port_asignado} (UDP)\n")

                while self._server_state:
                    data, addr = s.recvfrom(1024)
                    if data:
                        print(f"\n[SERVER] Message received from {addr}\n")
                        self._NODE.on_recv(data.decode())

        except Exception as e:
            import random            
            print(f"\n[SERVER] Error: {e}\n")
            self.set_port(random.randint(1024, 65535))
            self._run_server(self._PORT)

    def init_server(self) -> None:
        """
        Lanza un hilo daemon para ejecutar _run_server().
        """
        import time
        t: threading.Thread = threading.Thread(
            target=self._run_server,
            args=[self._PORT],
            daemon=self._DAEMON
        )
        t.start()
        print("\n[SERVER] Starting server...\n")
        time.sleep(1)  # Pequeña espera para asegurar que arranque el socket

    def close_server(self) -> None:
        self._server_state = False

    def is_port_in_use(self, port: int) -> bool:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(1)
            result = s.connect_ex((self._ADDRESS, port))
            return result == 0

    def set_port(self, port: int) -> int:
        """
        Si el puerto ya está en uso, incrementa hasta encontrar uno libre.
        Actualiza self._PORT y lo devuelve.
        """
        while 1024 <= port <= 65535 and self.is_port_in_use(port):
            port += 1

        self._PORT = port
        return port

