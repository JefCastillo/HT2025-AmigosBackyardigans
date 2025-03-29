import socket
import json
import cv2
import numpy as np
from datetime import datetime
from threading import Thread, Lock
import time

class SemaforoReceptor:
    def __init__(self):
        self.host = '127.0.0.1'
        self.port = 65432
        self.estado_actual = "desconocido"
        self.tiempo_restante = 0
        self.vehiculos = 0
        self.running = True
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.data_lock = Lock()
        
        # Configuración de la ventana
        self.window_name = "Monitor de Semaforo Inteligente"
        cv2.namedWindow(self.window_name, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(self.window_name, 800, 600)
        
    def dibujar_interfaz(self):
        # Crear imagen base
        img = np.zeros((600, 800, 3), dtype=np.uint8)
        
        # Título
        cv2.putText(img, "MONITOR DE SEMAFORO INTELIGENTE", (100, 40), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 255), 2)
        
        # Panel del semáforo (izquierda)
        self.dibujar_semaforo(img, 50, 80, 300, 480)
        
        # Panel de información (derecha)
        self.dibujar_panel_info(img, 400, 80, 350, 480)
        
        # Panel de estado (inferior)
        self.dibujar_panel_estado(img, 50, 520, 700, 60)
        
        return img
    
    def dibujar_semaforo(self, img, x, y, w, h):
        # Fondo del panel
        cv2.rectangle(img, (x, y), (x+w, y+h), (40, 40, 40), -1)
        cv2.rectangle(img, (x, y), (x+w, y+h), (100, 100, 100), 2)
        
        # Luces del semáforo
        colores = {
            "rojo": (0, 0, 255),
            "amarillo": (0, 255, 255),
            "verde": (0, 255, 0),
            "desconocido": (100, 100, 100)
        }
        
        centro_x = x + w // 2
        radio = 50
        
        for i, (nombre, color) in enumerate(colores.items()):
            if nombre == "desconocido":
                continue
                
            luz_y = y + 80 + i * 120
            estado_color = color if nombre == self.estado_actual else (30, 30, 30)
            
            # Dibujar luz
            cv2.circle(img, (centro_x, luz_y), radio, estado_color, -1)
            cv2.circle(img, (centro_x, luz_y), radio, (200, 200, 200), 2)
            
            # Etiqueta
            cv2.putText(img, nombre.upper(), (centro_x - 50, luz_y + 80), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 1)
            
            # Tiempo si está activo
            if nombre == self.estado_actual and self.estado_actual != "desconocido":
                cv2.putText(img, f"{self.tiempo_restante}s", 
                           (centro_x - 20, luz_y + 110), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    
    def dibujar_panel_info(self, img, x, y, w, h):
        # Fondo del panel
        cv2.rectangle(img, (x, y), (x+w, y+h), (30, 30, 60), -1)
        cv2.rectangle(img, (x, y), (x+w, y+h), (100, 100, 200), 2)
        
        # Título
        cv2.putText(img, "INFORMACION DE TRAFICO", (x+20, y+30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 1)
        
        # Información
        info = [
            f"Vehiculos detectados: {self.vehiculos}",
            f"Estado actual: {self.estado_actual.upper()}",
            f"Tiempo restante: {self.tiempo_restante} segundos",
            "",
            "Historial reciente:",
            f"Ultima actualizacion:",
            datetime.now().strftime("%H:%M:%S")
        ]
        
        for i, texto in enumerate(info):
            cv2.putText(img, texto, (x+20, y+80 + i*30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
        
        # Gráfico simple de vehículos
        max_vehiculos = 20
        nivel = min(self.vehiculos / max_vehiculos, 1.0) if self.vehiculos > 0 else 0
        bar_height = int(200 * nivel)
        
        cv2.rectangle(img, (x+200, y+250), (x+250, y+450), (50, 50, 50), -1)
        cv2.rectangle(img, (x+200, y+450 - bar_height), 
                     (x+250, y+450), (0, int(255 * nivel), 255 - int(255 * nivel)), -1)
        
        cv2.putText(img, "Nivel de trafico", (x+180, y+230), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
    
    def dibujar_panel_estado(self, img, x, y, w, h):
        # Fondo del panel
        cv2.rectangle(img, (x, y), (x+w, y+h), (40, 40, 40), -1)
        cv2.rectangle(img, (x, y), (x+w, y+h), (100, 100, 100), 2)
        
        # Mensaje de estado
        status_msg = "CONECTADO" if self.estado_actual != "desconocido" else "ESPERANDO CONEXION"
        status_color = (0, 255, 0) if self.estado_actual != "desconocido" else (0, 0, 255)
        
        cv2.putText(img, f"Estado: {status_msg}", (x+20, y+30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, status_color, 1)
        
        cv2.putText(img, "Presione 'Q' para salir", (x+500, y+30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)
    
    def recibir_datos(self):
        try:
            self.socket.bind((self.host, self.port))
            self.socket.listen()
            print(f"Servidor listo en {self.host}:{self.port}")
            
            while self.running:
                try:
                    conn, addr = self.socket.accept()
                    print(f"Conexión establecida con {addr}")
                    
                    while self.running:
                        try:
                            data = conn.recv(1024)
                            if not data:
                                break
                            
                            try:
                                datos = json.loads(data.decode('utf-8'))
                                with self.data_lock:
                                    self.estado_actual = datos.get("estado", "desconocido")
                                    self.tiempo_restante = int(datos.get("tiempo", 0))
                                    self.vehiculos = datos.get("vehiculos", 0)
                                print(f"Datos recibidos: {datos}")
                            except (json.JSONDecodeError, ValueError) as e:
                                print(f"Error decodificando datos: {str(e)}")
                            
                        except ConnectionResetError:
                            print("Conexión perdida con el cliente")
                            break
                        except Exception as e:
                            print(f"Error al recibir datos: {str(e)}")
                            break
                    
                    conn.close()
                    with self.data_lock:
                        self.estado_actual = "desconocido"
                        self.tiempo_restante = 0
                        self.vehiculos = 0
                    print("Esperando nueva conexión...")
                    
                except socket.timeout:
                    continue
                except OSError as e:
                    if self.running:
                        print(f"Error en conexión: {str(e)}")
                        break
                except Exception as e:
                    print(f"Error inesperado: {str(e)}")
                    time.sleep(1)
                    
        finally:
            if self.socket:
                self.socket.close()
    
    def mostrar_interfaz(self):
        while self.running:
            img = self.dibujar_interfaz()
            cv2.imshow(self.window_name, img)
            
            key = cv2.waitKey(100)
            if key == ord('q') or cv2.getWindowProperty(self.window_name, cv2.WND_PROP_VISIBLE) < 1:
                self.running = False
        
        cv2.destroyAllWindows()
    
    def ejecutar(self):
        # Hilo para recibir datos
        receiver_thread = Thread(target=self.recibir_datos, daemon=True)
        receiver_thread.start()
        
        # Mostrar interfaz en el hilo principal
        self.mostrar_interfaz()
        
        # Limpieza
        self.socket.close()
        print("Servidor detenido")

if __name__ == "__main__":
    receptor = SemaforoReceptor()
    receptor.ejecutar()