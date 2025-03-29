import cv2
import numpy as np
import time
from threading import Thread, Lock
import socket
import json

class SemaforoEmisor:
    def __init__(self):
        # Configuración YOLO
        try:
            self.net = cv2.dnn.readNet("yolov3.weights", "yolov3.cfg")
            with open("coco.names", "r") as f:
                self.classes = [line.strip() for line in f.readlines()]
        except Exception as e:
            print(f"Error cargando modelos YOLO: {str(e)}")
            exit(1)
        
        self.vehicle_classes = [2, 5, 7]  # car, bus, truck
        self.layer_names = self.net.getLayerNames()
        self.output_layers = [self.layer_names[i-1] for i in self.net.getUnconnectedOutLayers()]
        
        # Estados del semáforo
        self.estados = {
            "rojo": (0, 0, 255),
            "amarillo": (0, 255, 255),
            "verde": (0, 255, 0)
        }
        self.estado_actual = "rojo"
        self.tiempo_restante = 0
        self.vehiculos_detectados = 0
        self.data_lock = Lock()
        self.running = True
        
        # Configuración de red
        self.host_receptor = '127.0.0.1'
        self.port_receptor = 65432
        
        # Configuración de ventana
        self.window_name = "Sistema de Semaforo Inteligente (Emisor)"
        cv2.namedWindow(self.window_name, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(self.window_name, 1200, 700)
    
    def detectar_vehiculos(self, frame):
        try:
            height, width = frame.shape[:2]
            blob = cv2.dnn.blobFromImage(frame, 1/255.0, (320, 320), swapRB=True, crop=False)
            self.net.setInput(blob)
            outs = self.net.forward(self.output_layers)
            
            vehiculos = 0
            boxes = []
            confidences = []
            
            for out in outs:
                for detection in out:
                    scores = detection[5:]
                    class_id = np.argmax(scores)
                    confidence = scores[class_id]
                    if confidence > 0.5 and class_id in self.vehicle_classes:
                        vehiculos += 1
                        box = detection[0:4] * np.array([width, height, width, height])
                        (center_x, center_y, w, h) = box.astype("int")
                        x = int(center_x - w/2)
                        y = int(center_y - h/2)
                        boxes.append([x, y, int(w), int(h)])
                        confidences.append(float(confidence))
            
            indexes = cv2.dnn.NMSBoxes(boxes, confidences, 0.5, 0.4)
            
            for i in indexes.flatten():
                x, y, w, h = boxes[i]
                cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
                cv2.putText(frame, f"{self.classes[class_id]} {confidence:.2f}", 
                          (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,255,0), 2)
            
            return vehiculos, frame
        except Exception as e:
            print(f"Error en detección: {str(e)}")
            return 0, frame
    
    def dibujar_panel_control(self, frame):
        try:
            panel = np.zeros((700, 400, 3), dtype=np.uint8)
            cv2.rectangle(panel, (0, 0), (400, 700), (40, 40, 40), -1)
            
            # Estado actual
            cv2.putText(panel, "ESTADO ACTUAL", (20, 40), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
            
            # Dibujar semáforo
            color_rojo = self.estados["rojo"] if self.estado_actual == "rojo" else (50, 50, 50)
            color_amarillo = self.estados["amarillo"] if self.estado_actual == "amarillo" else (50, 50, 50)
            color_verde = self.estados["verde"] if self.estado_actual == "verde" else (50, 50, 50)
            
            cv2.circle(panel, (200, 150), 50, color_rojo, -1)
            cv2.circle(panel, (200, 250), 50, color_amarillo, -1)
            cv2.circle(panel, (200, 350), 50, color_verde, -1)
            
            # Información
            cv2.putText(panel, f"Estado: {self.estado_actual.upper()}", (20, 450), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 1)
            cv2.putText(panel, f"Tiempo: {self.tiempo_restante}s", (20, 500), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 1)
            cv2.putText(panel, f"Vehiculos: {self.vehiculos_detectados}", (20, 550), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 1)
            cv2.putText(panel, "Presione 'Q' para salir", (20, 650), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)
            
            return panel
        except Exception as e:
            print(f"Error dibujando panel: {str(e)}")
            return np.zeros((700, 400, 3), dtype=np.uint8)

    def actualizar_estado(self):
        while self.running:
            if self.estado_actual == "rojo":
                # Tiempo base para rojo (sin cambios)
                self.tiempo_restante = 10
                while self.tiempo_restante > 0 and self.running:
                    time.sleep(1)
                    self.tiempo_restante -= 1
                if self.running:
                    self.estado_actual = "verde"
                    
            elif self.estado_actual == "verde":
                # LÓGICA DE TIEMPO DINÁMICO (aquí implementamos el cambio)
                tiempo_base = 15  # Tiempo mínimo en verde
                incremento_por_vehiculo = 2  # Segundos extra por cada vehículo
                max_tiempo = 30  # Tiempo máximo permitido
                
                with self.data_lock:
                    tiempo_final = min(
                        tiempo_base + (self.vehiculos_detectados * incremento_por_vehiculo),
                        max_tiempo
                    )
                    self.tiempo_restante = tiempo_final
                
                while self.tiempo_restante > 0 and self.running:
                    time.sleep(1)
                    self.tiempo_restante -= 1
                if self.running:
                    self.estado_actual = "amarillo"
                    
            else:  # Estado amarillo
                self.tiempo_restante = 3  # Tiempo fijo para amarillo
                while self.tiempo_restante > 0 and self.running:
                    time.sleep(1)
                    self.tiempo_restante -= 1
                if self.running:
                    self.estado_actual = "rojo"

    def enviar_datos(self):
        try:
            while self.running:
                try:
                    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                        s.settimeout(2)
                        s.connect((self.host_receptor, self.port_receptor))
                        print(f"Conectado al servidor en {self.host_receptor}:{self.port_receptor}")
                        
                        while self.running:
                            with self.data_lock:
                                data = {
                                    "estado": self.estado_actual,
                                    "tiempo": self.tiempo_restante,
                                    "vehiculos": self.vehiculos_detectados,
                                    "timestamp": time.time()
                                }
                            
                            try:
                                s.sendall(json.dumps(data).encode('utf-8'))
                                time.sleep(0.5)
                            except (ConnectionResetError, BrokenPipeError) as e:
                                print(f"Conexión perdida: {str(e)}. Reconectando...")
                                break
                            except Exception as e:
                                print(f"Error al enviar: {str(e)}")
                                break
                                
                except (ConnectionRefusedError, socket.timeout) as e:
                    print(f"Servidor no disponible: {str(e)}. Reintentando en 3 segundos...")
                    time.sleep(3)
                except Exception as e:
                    print(f"Error en conexión: {str(e)}")
                    time.sleep(3)
        except Exception as e:
            print(f"Error en hilo de envío: {str(e)}")
            self.running = False

    def procesar_video(self):
        try:
            cap = cv2.VideoCapture("video1.mp4")
            
            if not cap.isOpened():
                print("Error: No se pudo abrir el video")
                self.running = False
                return
            
            while self.running and cap.isOpened():
                ret, frame = cap.read()
                if not ret:
                    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    continue
                
                # Detección de vehículos
                vehiculos, frame_detectado = self.detectar_vehiculos(frame)
                
                with self.data_lock:
                    self.vehiculos_detectados = vehiculos
                
                # Redimensionar video
                frame_detectado = cv2.resize(frame_detectado, (800, 700))
                
                # Crear panel de control
                panel_control = self.dibujar_panel_control(frame_detectado)
                
                # Combinar frames
                combined = np.hstack((frame_detectado, panel_control))
                
                # Mostrar ventana
                cv2.imshow(self.window_name, combined)
                
                # Espera activa para la tecla 'q'
                key = cv2.waitKey(30) & 0xFF
                if key == ord('q') or cv2.getWindowProperty(self.window_name, cv2.WND_PROP_VISIBLE) < 1:
                    self.running = False
            
            cap.release()
            cv2.destroyAllWindows()
        except Exception as e:
            print(f"Error en procesamiento de video: {str(e)}")
            self.running = False

    def ejecutar(self):
        try:
            # Iniciar hilos
            Thread(target=self.actualizar_estado, daemon=True).start()
            Thread(target=self.enviar_datos, daemon=True).start()
            
            # Procesar video en el hilo principal
            self.procesar_video()
            
            # Detener todos los hilos
            self.running = False
            print("Sistema detenido correctamente")
        except Exception as e:
            print(f"Error en ejecución: {str(e)}")
        finally:
            cv2.destroyAllWindows()

if __name__ == "__main__":
    emisor = SemaforoEmisor()
    emisor.ejecutar()