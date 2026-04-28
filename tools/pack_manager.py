import os
import json
import argparse

PACKS_DIR = os.path.join(os.path.dirname(__file__), '../shards')

class PackManager:
    def list_packs(self):
        """List all available packs."""
        packs = [d for d in os.listdir(PACKS_DIR) if os.path.isdir(os.path.join(PACKS_DIR, d))]
        print("Available Packs:")
        for pack in packs:
            print(f"- {pack}")

    def install_pack(self, pack_name):
        """Install a pack by name."""
        pack_path = os.path.join(PACKS_DIR, pack_name)
        if os.path.exists(pack_path):
            print(f"Pack '{pack_name}' is already installed.")
        else:
            os.makedirs(pack_path)
            with open(os.path.join(pack_path, 'pack.json'), 'w') as f:
                json.dump({"name": pack_name, "version": "1.0.0"}, f, indent=4)
            print(f"Pack '{pack_name}' installed successfully.")

    def remove_pack(self, pack_name):
        """Remove a pack by name."""
        pack_path = os.path.join(PACKS_DIR, pack_name)
        if os.path.exists(pack_path):
            for root, dirs, files in os.walk(pack_path, topdown=False):
                for name in files:
                    os.remove(os.path.join(root, name))
                for name in dirs:
                    os.rmdir(os.path.join(root, name))
            os.rmdir(pack_path)
            print(f"Pack '{pack_name}' removed successfully.")
        else:
            print(f"Pack '{pack_name}' does not exist.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Pack Manager for Erasmus X")
    parser.add_argument("command", choices=["list", "install", "remove"], help="Command to execute")
    parser.add_argument("pack_name", nargs="?", help="Name of the pack (for install/remove)")

    args = parser.parse_args()
    manager = PackManager()

    if args.command == "list":
        manager.list_packs()
    elif args.command == "install" and args.pack_name:
        manager.install_pack(args.pack_name)
    elif args.command == "remove" and args.pack_name:
        manager.remove_pack(args.pack_name)
    else:
        print("Invalid command or missing pack name.")