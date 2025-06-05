/********************************************************************************
 * Implementación de un Nodo P2P en ESP32 con ESP-NOW (Versión Final v2.4)
 * * Añadido indicador LED para visualizar el tráfico de red en OnDataRecv.
 ********************************************************************************/

#include <esp_now.h>
#include <WiFi.h>
#include <esp_wifi.h>
#include <string>
#include <vector>

// --- CONFIGURACIÓN DEL PROTOCOLO ---
#define TYPE_BROADCAST 0
#define TYPE_UNICAST   1
#define MAX_HOP        10
#define MAX_PAYLOAD_LEN 128
#define ROUTING_TABLE_SIZE 20
#define MSG_REGISTER_SIZE 20

// <<<<<<< 1. DEFINIR EL PIN DEL LED >>>>>>>>>
// La mayoría de las placas ESP32 tienen el LED integrado en el pin 2.
const int LED_PIN = 2;


// --- ESTRUCTURAS DE DATOS ---
const uint8_t broadcastAddress[] = {0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF};
String node_name = "ESP32_Node";
uint8_t my_mac[6];

typedef struct __attribute__((packed)) p2p_message {
  char id[32];
  int type;
  uint8_t origin_mac[6];
  uint8_t destine_mac[6];
  uint8_t previous_mac[6];
  char payload[MAX_PAYLOAD_LEN];
  int hop_count;
} p2p_message;

typedef struct {
  uint8_t destine_mac[6];
  uint8_t next_hop_mac[6];
  int hop_count;
} RoutingTableEntry;

// --- VARIABLES GLOBALES ---
RoutingTableEntry routingTable[ROUTING_TABLE_SIZE];
int routing_table_count = 0;
String messageRegister[MSG_REGISTER_SIZE];
int msg_register_idx = 0;


// --- PROTOTIPOS DE FUNCIONES ---
void send_message(const uint8_t* dest_mac, const char* payload, p2p_message* existing_msg = nullptr);
void mac_str_to_uint8(const String& mac_str, uint8_t* arr);
void print_mac(const uint8_t* mac_addr);
void register_trace(const uint8_t* dest, const uint8_t* next_hop, int hops);


// --- FUNCIONES AUXILIARES ---
void mac_str_to_uint8(const String& mac_str, uint8_t* arr) {
  int a, b, c, d, e, f;
  sscanf(mac_str.c_str(), "%x:%x:%x:%x:%x:%x", &a, &b, &c, &d, &e, &f);
  arr[0] = a; arr[1] = b; arr[2] = c; arr[3] = d; arr[4] = e; arr[5] = f;
}

void print_mac(const uint8_t* mac_addr) {
  char macStr[18];
  snprintf(macStr, sizeof(macStr), "%02X:%02X:%02X:%02X:%02X:%02X", mac_addr[0], mac_addr[1], mac_addr[2], mac_addr[3], mac_addr[4], mac_addr[5]);
  Serial.print(macStr);
}

void generate_unique_id(char* id_buffer) {
  snprintf(id_buffer, 32, "%02X%02X%02X%02X%02X%02X-%lu", my_mac[0], my_mac[1], my_mac[2], my_mac[3], my_mac[4], my_mac[5], millis());
}

bool wasMessageSeen(const String& msg_id) {
  for (int i = 0; i < MSG_REGISTER_SIZE; ++i) {
    if (messageRegister[i] == msg_id) return true;
  }
  return false;
}

void registerMessageId(const String& msg_id) {
  messageRegister[msg_register_idx] = msg_id;
  msg_register_idx = (msg_register_idx + 1) % MSG_REGISTER_SIZE;
}

void register_trace(const uint8_t* dest, const uint8_t* next_hop, int hops) {
    if (memcmp(dest, my_mac, 6) == 0) return;
    for (int i = 0; i < routing_table_count; ++i) {
        if (memcmp(routingTable[i].destine_mac, dest, 6) == 0) {
            if (hops < routingTable[i].hop_count) {
                memcpy(routingTable[i].next_hop_mac, next_hop, 6);
                routingTable[i].hop_count = hops;
                Serial.print("[RT] Ruta actualizada para "); print_mac(dest); Serial.println();
            }
            return;
        }
    }
    if (routing_table_count < ROUTING_TABLE_SIZE) {
        memcpy(routingTable[routing_table_count].destine_mac, dest, 6);
        memcpy(routingTable[routing_table_count].next_hop_mac, next_hop, 6);
        routingTable[routing_table_count].hop_count = hops;
        routing_table_count++;
        Serial.print("[RT] Nueva ruta añadida para "); print_mac(dest); Serial.println();
    }
}


// --- FUNCIONES CORE DE ESP-NOW ---
void join_peer(const uint8_t* mac_addr) {
  esp_now_peer_info_t peerInfo = {};
  memcpy(peerInfo.peer_addr, mac_addr, 6);
  peerInfo.channel = 0;
  peerInfo.encrypt = false;
  
  if (!esp_now_is_peer_exist(mac_addr)) {
    if (esp_now_add_peer(&peerInfo) != ESP_OK) {
      Serial.println("[ERROR] No se pudo añadir el peer.");
      return;
    }
    Serial.print("[INFO] Peer "); print_mac(mac_addr); Serial.println(" añadido a ESP-NOW.");
  }

  register_trace(mac_addr, mac_addr, 1);
}

void leave_peer(const uint8_t* mac_addr) {
  if (esp_now_del_peer(mac_addr) != ESP_OK) {
    Serial.println("[ERROR] No se pudo eliminar el peer.");
    return;
  }
  Serial.print("[INFO] Peer "); print_mac(mac_addr); Serial.println(" eliminado.");
}

void OnDataSent(const uint8_t *mac_addr, esp_now_send_status_t status) {
  Serial.print("\r\n[INFO] Estado del último envío a "); print_mac(mac_addr);
  Serial.println(status == ESP_NOW_SEND_SUCCESS ? ": Entregado" : ": Falló");
}

void broadcast_message(const char* payload) {
  p2p_message msg = {};
  generate_unique_id(msg.id);
  msg.type = TYPE_BROADCAST;
  memcpy(msg.origin_mac, my_mac, 6);
  memset(msg.destine_mac, 0, 6); 
  memcpy(msg.previous_mac, my_mac, 6);
  strncpy(msg.payload, payload, MAX_PAYLOAD_LEN);
  msg.hop_count = 0;
  registerMessageId(msg.id);
  esp_now_send(broadcastAddress, (uint8_t *) &msg, sizeof(msg));
}

// =============================================================================
// FUNCIÓN OnDataRecv CON LA LÓGICA DE PARPADEO DEL LED
// =============================================================================
void OnDataRecv(const esp_now_recv_info * info, const uint8_t *incomingData, int len) {
  // <<<<<<< 3. LÓGICA DE PARPADEO DEL LED >>>>>>>>>
  // Al inicio de la función, hacemos parpadear el LED para indicar que se recibió un paquete.
  digitalWrite(LED_PIN, HIGH);
  delay(100); // Un parpadeo corto de 100 milisegundos
  digitalWrite(LED_PIN, LOW);

  const uint8_t* mac = info->src_addr;
  
  p2p_message msg;
  memcpy(&msg, incomingData, sizeof(msg));

  Serial.println("\n--- PAQUETE RECIBIDO ---");
  Serial.print("Desde: "); print_mac(mac);
  Serial.print(" | Origen final: "); print_mac(msg.origin_mac);
  Serial.print(" | Tipo: "); Serial.print(msg.type == TYPE_UNICAST ? "UNICAST" : "BROADCAST");
  Serial.print(" | Saltos: "); Serial.println(msg.hop_count);

  if (msg.hop_count >= MAX_HOP || wasMessageSeen(msg.id)) {
    Serial.println("[DESCARTADO] Demasiados saltos o mensaje duplicado.");
    return;
  }
  registerMessageId(msg.id);
  msg.hop_count++;

  register_trace(msg.origin_mac, mac, msg.hop_count);
  
  bool is_dest_null = true;
  for(int i = 0; i < 6; ++i) {
    if(msg.destine_mac[i] != 0) {
      is_dest_null = false;
      break;
    }
  }

  if (memcmp(msg.destine_mac, my_mac, 6) == 0) {
    Serial.println("[MENSAJE PARA MÍ]");
    Serial.printf("Payload: %s\n", msg.payload);

    if (msg.type == TYPE_BROADCAST) {
        Serial.println("[INFO] Mensaje de descubrimiento recibido. Enviando confirmación de ruta...");
        send_message(msg.origin_mac, "Ruta encontrada");
    }
  }
  else if (is_dest_null && msg.type == TYPE_BROADCAST) {
    Serial.println("[BROADCAST PURO RECIBIDO]");
    Serial.printf("Payload: %s\n", msg.payload);
    
    Serial.println("[INFO] Reenviando broadcast puro...");
    memcpy(msg.previous_mac, my_mac, 6);
    esp_now_send(broadcastAddress, (uint8_t *)&msg, sizeof(msg));
  }
  else if (msg.type == TYPE_BROADCAST) {
    Serial.println("[BROADCAST DE DESCUBRIMIENTO DE PASO. REENVIANDO...]");
    memcpy(msg.previous_mac, my_mac, 6);
    esp_now_send(broadcastAddress, (uint8_t *)&msg, sizeof(msg));
  }
  else {
    Serial.println("[REENVIANDO PAQUETE UNICAST]");
    send_message(nullptr, nullptr, &msg);
  }
  Serial.println("--- FIN DEL PROCESAMIENTO ---\n");
}


void send_message(const uint8_t* dest_mac, const char* payload, p2p_message* existing_msg) {
  p2p_message msg;
  bool is_forwarding = (existing_msg != nullptr);

  if (is_forwarding) {
    memcpy(&msg, existing_msg, sizeof(p2p_message));
  } else {
    generate_unique_id(msg.id);
    msg.type = TYPE_UNICAST;
    memcpy(msg.origin_mac, my_mac, 6);
    memcpy(msg.destine_mac, dest_mac, 6);
    strncpy(msg.payload, payload, MAX_PAYLOAD_LEN);
    msg.hop_count = 0;
    registerMessageId(msg.id);
  }

  memcpy(msg.previous_mac, my_mac, 6);

  uint8_t next_hop[6];
  bool route_found = false;

  for (int i = 0; i < routing_table_count; ++i) {
    if (memcmp(routingTable[i].destine_mac, msg.destine_mac, 6) == 0) {
      memcpy(next_hop, routingTable[i].next_hop_mac, 6);
      route_found = true;
      break;
    }
  }

  if (route_found) {
    join_peer(next_hop);
    Serial.print("[UNICAST] Ruta conocida. Enviando a "); print_mac(next_hop); Serial.println();
    esp_now_send(next_hop, (uint8_t *)&msg, sizeof(msg));
  } else {
    Serial.println("[INFO] Sin ruta. Enviando broadcast de descubrimiento...");
    msg.type = TYPE_BROADCAST; 
    esp_now_send(broadcastAddress, (uint8_t *)&msg, sizeof(msg));
  }
}

void print_node_info() {
    Serial.println("\n--- INFO DEL NODO ---");
    Serial.print("Nombre: "); Serial.println(node_name);
    Serial.print("MAC: "); print_mac(my_mac); Serial.println();
    Serial.println("---------------------\n");
}

void print_routing_table() {
    Serial.println("\n--- TABLA DE ENRUTAMIENTO ---");
    if (routing_table_count == 0) {
        Serial.println("¡Vacía!");
    }
    for (int i = 0; i < routing_table_count; ++i) {
        Serial.print("Destino: "); print_mac(routingTable[i].destine_mac);
        Serial.print(" | Siguiente Salto: "); print_mac(routingTable[i].next_hop_mac);
        Serial.print(" | Saltos: "); Serial.println(routingTable[i].hop_count);
    }
    Serial.println("-----------------------------\n");
}


// --- SETUP Y LOOP PRINCIPAL ---
void setup() {
  Serial.begin(115200);
  delay(1000);
  Serial.println();
  
  // <<<<<<< 2. CONFIGURAR EL PIN DEL LED COMO SALIDA >>>>>>>>>
  pinMode(LED_PIN, OUTPUT);
  digitalWrite(LED_PIN, LOW); // Nos aseguramos que empiece apagado
  
  WiFi.mode(WIFI_STA);
  esp_wifi_get_mac(WIFI_IF_STA, my_mac);

  if (esp_now_init() != ESP_OK) {
    Serial.println("[FATAL] Error inicializando ESP-NOW");
    return;
  }

  esp_now_register_send_cb(OnDataSent);
  esp_now_register_recv_cb(OnDataRecv);

  join_peer(broadcastAddress);

  print_node_info();
  Serial.println("Nodo P2P inicializado. Esperando comandos...");
  Serial.println("Comandos: join, leave, send, broadcast, rt, info");
}

void loop() {
  if (Serial.available()) {
    String command = Serial.readStringUntil('\n');
    command.trim();
    
    std::vector<String> args;
    int last_space = -1;
    for(int i = 0; i < command.length(); i++) {
        if(command.charAt(i) == ' '){
            args.push_back(command.substring(last_space + 1, i));
            last_space = i;
        }
    }
    args.push_back(command.substring(last_space + 1));

    String cmd = args[0];
    cmd.toLowerCase();

    if (cmd == "join" && args.size() >= 2) {
      uint8_t mac[6];
      mac_str_to_uint8(args[1], mac);
      join_peer(mac);
    } 
    else if (cmd == "leave" && args.size() >= 2) {
      uint8_t mac[6];
      mac_str_to_uint8(args[1], mac);
      leave_peer(mac);
    }
    else if (cmd == "send" && args.size() >= 3) {
      uint8_t mac[6];
      mac_str_to_uint8(args[1], mac);
      String msg_payload = command.substring(args[0].length() + args[1].length() + 2);
      send_message(mac, msg_payload.c_str());
    }
    else if (cmd == "broadcast" && args.size() >= 2) {
      String msg_payload = command.substring(args[0].length() + 1);
      broadcast_message(msg_payload.c_str());
    }
    else if (cmd == "rt") {
      print_routing_table();
    }
    else if (cmd == "info") {
      print_node_info();
    }
    else {
      Serial.println("[ERROR] Comando desconocido o argumentos incorrectos.");
    }
  }
}