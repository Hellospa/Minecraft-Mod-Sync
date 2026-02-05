import toml
import os
import requests

def get_config():
    config_path = os.path.join(os.path.dirname(__file__), 'config.toml')
    with open(config_path, 'r', encoding='utf-8') as f:
        config = toml.load(f)
    return config

config = get_config()

class Client:
    def __init__(self):
        self.server_address = config['server_address']
        self.server_port = config['server_port']
        self.userurl = f"http://{self.server_address}:{self.server_port}"

        response = requests.get(f"{self.userurl}/status")
        if response.status_code == 200:
            status_data = response.json()
            print(f"已连接到\x1b[1;36mFreedom Create\x1b[0m服务器")
            print(status_data)
            self.sync_mods()
        else:
            print("\x1b[31m无法连接到服务器\x1b[0m")
            print("请检查配置文件中的服务器地址和端口是否正确，确保服务器正在运行")
            print(f"配置文件中的服务器地址：{self.server_address}:{self.server_port}")
    def sync_mods(self):
        minecraft_dir = config['minecraft_dir']
        mod_list_response = requests.get(f"{self.userurl}/list_mods")
        if mod_list_response.status_code != 200:
            print(f"\x1b[31m无法从服务器获取模组列表，状态码：{mod_list_response.status_code}\x1b[0m")
            return
        mod_list = mod_list_response.json()
        print(f"已获取到模组列表，获取到{len(mod_list['mods'])}个模组，开始同步模组...")
        self_mods = self.self_mod_list(mod_list['covered_mod_dir'])

        for mod in mod_list['mods']:
            if mod not in self_mods:
                download_url = f"{self.userurl}/download/{mod['path']}"
                response = requests.get(download_url, stream=True)
                if response.status_code == 200:
                    dest_path = os.path.join(minecraft_dir, mod['path'])
                    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                    
                    mod_size = mod['size']
                    downloaded_size = 0
                    mod_name = mod['path'].split('/')[-1]

                    with open(dest_path, 'wb') as f:
                        for chunk in response.iter_content(chunk_size=8192):
                            if chunk:
                                f.write(chunk)
                                downloaded_size += len(chunk)
                                done = int(50 * downloaded_size / mod_size)
                                print("\x1b[2K", end='')  # 清除当前行
                                print("\x1b[1F", end='')  # 光标上移一行
                                print(f"\r正在下载[{mod_name}] [{'=' * done}{' '*(50-done)}] {downloaded_size}/{mod_size} 字节", end='')
                    print(f"已下载模组：{mod['path']}，大小：{mod_size} 字节")
                else:
                    print(f"\x1b[31m无法下载模组 {mod['path']}，状态码：{response.status_code}\x1b[0m")
            else:
                print(f"模组 {mod['path']} 已存在于本地，跳过同步")
                self_mods.remove(mod)

        if len(self_mods) > 0:
            print(f"\n检测到本地有 {len(self_mods)} 个多余模组，建议删除以保持与服务器同步：")
            for mod in self_mods:
                print(f" - {mod['path']}")
            print("需要自动删除吗? [y(是)/n(否)/a(以后都自动删除)] ", end='')
            choice = input().strip().lower()
            if choice == 'y' or (choice == 'a' and config.get('always_automiac_del_mods', False)):
                for mod in self_mods:
                    mod_path = os.path.join(minecraft_dir, mod['path'])
                    if os.path.exists(mod_path):
                        os.remove(mod_path)
                        print(f"已删除多余模组：{mod['path']}")
                if choice == 'a':
                    config['always_automiac_del_mods'] = True
                    with open(os.path.join(os.path.dirname(__file__), 'config.toml'), 'w') as f:
                        toml.dump(config, f)
            else:
                print("未删除多余模组")

        print("模组同步完成！")
    def self_mod_list(self, covered_mod_dir):
        json_data = []
        for i in covered_mod_dir:
            for root, dirs, files in os.walk(config['minecraft_dir'] + '/' + i):
                for file in files:
                    file_path = os.path.join(root, file)
                    relative_path = os.path.relpath(file_path, config['minecraft_dir'])
                    file_size = os.path.getsize(file_path)
                    json_data.append({'path': relative_path, 'size': file_size})
        return json_data
if __name__ == '__main__':
    client = Client()