import grpc
from concurrent import futures
import energy_databroker_pb2
import energy_databroker_pb2_grpc
import os

class DatabrokerServicer(energy_databroker_pb2_grpc.DatabrokerServicer):
    def energydatabroker(self, request, context):
        path_to_csv = "../data/train_energy_data.csv"
        return energy_databroker_pb2.TrainRequest(csv_file_path=path_to_csv)

def serve():
    port = "8061"
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    energy_databroker_pb2_grpc.add_DatabrokerServicer_to_server(DatabrokerServicer(),server)
    server.add_insecure_port("[::]:" + port)
    server.start()
    print("Databroker Service is running on port: " + port)
    print("Current Path: " + os.getcwd())
    server.wait_for_termination()

if __name__ == "__main__":
    serve()