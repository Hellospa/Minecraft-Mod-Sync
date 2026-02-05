from threading import Thread
import flask
import toml
import os

def get_config():
    config_path = os.path.join(os.path.dirname(__file__), 'config.toml')
    with open(config_path, 'r', encoding='utf-8') as f:
        config = toml.load(f)
    return config

config = get_config()

class Server:
    def __init__(self, ip: str, port: int):
        self.ip = ip
        self.port = port

        os.makedirs('download_temp', exist_ok=True)
        os.makedirs('base', exist_ok=True)
        self.app = flask.Flask(__name__)

    def setup_routes(self):
        @self.app.route('/status', methods=['GET'])
        def status(): # 服务器状态
            mod_count = 0
            for i in config['sync_mod_dir']:
                for root, dirs, files in os.walk('base/' + i):
                    mod_count += len(files)
            return flask.jsonify({'status': 'ok', 'mod_count': mod_count})
        @self.app.route('/list_mods', methods=['GET'])
        def list_mods(): # 列出所有模组
            json_data = []
            for i in config['sync_mod_dir']:
                for root, dirs, files in os.walk('base/' + i):
                    for file in files:
                        file_path = os.path.join(root, file)
                        relative_path = os.path.relpath(file_path, 'base')
                        file_size = os.path.getsize(file_path)
                        json_data.append({'path': relative_path, 'size': file_size})
            return flask.jsonify(mods = json_data, covered_mod_dir = config['sync_mod_dir'])
        @self.app.route('/sync_minecraft_dir', methods=['POST'])
        def sync_minecraft_dir(): # 同步.minecraft目录
            minecraft_dir = config['sync_minecraft_dir']
            for i in config['sync_mod_dir']:
                os.path.exists('base/' + i) or os.makedirs('base/' + i) # type: ignore
                for root, dirs, files in os.walk(minecraft_dir + '/' + i):
                    for file in files:
                        file_path = os.path.join(root, file)
                        relative_path = os.path.relpath(file_path, minecraft_dir)
                        dest_path = os.path.join('base', relative_path)
                        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                        with open(file_path, 'rb') as src_file, open(dest_path, 'wb') as dest_file:
                            while True:
                                chunk = src_file.read(config['chunk_size'])
                                if not chunk:
                                    break
                                dest_file.write(chunk)
            return flask.jsonify({'status': 'sync complete'})
        @self.app.route('/download/<path:filepath>', methods=['GET'])
        def download(filepath): # 下载模组文件
            filepath = os.path.join('base', filepath)
            if os.path.exists(filepath):
                return flask.send_file(filepath, as_attachment=True)
            else:
                return flask.abort(404)

def panel(server: Server):
    print("服务器管理面板")
    while True:
        print("1. 服务器状态 status")
        print("2. 列出所有模组 list_mods")
        print("3. 同步.minecraft目录 sync_minecraft_dir")
        print("4. 下载模组文件 download <filepath>")
        print("5. 退出 exit")
        cmd = input("请输入命令：").strip().lower()
        if cmd == '1':
            print(server.app.test_client().get('/status').json)
        elif cmd == '2':
            print(server.app.test_client().get('/list_mods').json)
        elif cmd == '3':
            print(server.app.test_client().post('/sync_minecraft_dir').json)
        elif cmd == '4':
            filepath = input("请输入文件路径：").strip()
            print(server.app.test_client().get('/download/' + filepath).status_code)
        elif cmd == '5':
            break
        else:
            print("未知命令")

if __name__ == '__main__':
    server = Server(config['ip'], config['port'])
    server.setup_routes()
    Thread(target=panel, args=(server,)).start()
    server.app.run(host=server.ip, port=server.port)
    