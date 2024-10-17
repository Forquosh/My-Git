import sys
import os
import time
import zlib
import hashlib
import struct
from typing import Tuple, cast
import urllib.request
from pathlib import Path


def create_object(category: str, data, parent=Path(os.getcwd())):
    header = f"{category} {len(data)}\x00"
    content = header.encode() + data
    sha = hashlib.sha1(content).hexdigest()
    p = parent / ".git" / "objects" / sha[:2] / sha[2:]
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(zlib.compress(content, level=zlib.Z_BEST_SPEED))
    return sha


def read_object(sha: str, parent=Path(os.getcwd())):
    path = parent / ".git" / "objects" / sha[:2] / sha[2:]
    bs = path.read_bytes()
    head, content = zlib.decompress(bs).split(b"\0", maxsplit=1)
    tip, _ = head.split(b" ")
    return tip.decode(), content


def write_tree(path: str):
    if os.path.isfile(path):
        with open(path, "rb") as f:
            data = f.read()
        return create_object("blob", data)

    contents = sorted(
        os.listdir(path),
        key=lambda x: x if os.path.isfile(os.path.join(path, x)) else f"{x}/",
    )

    tree_entries = b""
    for item in contents:
        if item == ".git":
            continue

        full_path = os.path.join(path, item)

        if os.path.isfile(full_path):
            mode = "100644"  # blob
            sha = write_tree(full_path)
        else:
            mode = "40000"  # tree
            sha = write_tree(full_path)

        tree_entries += f"{mode} {item}\0".encode() + int(sha, 16).to_bytes(20, byteorder="big")

    tree_content = f"tree {len(tree_entries)}\0".encode() + tree_entries
    sha = hashlib.sha1(tree_content).hexdigest()

    tree_path = Path(f".git/objects/{sha[:2]}/{sha[2:]}")
    tree_path.parent.mkdir(parents=True, exist_ok=True)
    with open(tree_path, "wb") as f:
        f.write(zlib.compress(tree_content))

    return sha


def main():
    command = sys.argv[1]
    if command == "init":
        os.mkdir(".git")
        os.mkdir(".git/objects")
        os.mkdir(".git/refs")
        with open(".git/HEAD", "w") as f:
            f.write("ref: refs/heads/main\n")
        print("Initialized git directory")

    elif command == "cat-file":
        if sys.argv[2] == "-p":
            blob_sha = sys.argv[3]
            with open(f".git/objects/{blob_sha[:2]}/{blob_sha[2:]}", "rb") as f:
                raw = zlib.decompress(f.read())
                header, content = raw.split(b"\0", maxsplit=1)
                print(content.decode("utf-8"), end="")

    elif command == "hash-object":
        if sys.argv[2] == "-w":
            file = sys.argv[3]
            with open(file, "rb") as f:
                data = f.read()
            sha = create_object("blob", data)
            print(sha, end="")

    elif command == "ls-tree":
        name_only = sys.argv[2] == "--name-only"
        sha = sys.argv[3] if name_only else sys.argv[2]
        with open(os.path.join(".git/objects", sha[:2], sha[2:]), "rb") as f:
            data = zlib.decompress(f.read())
            _, tree_data = data.split(b"\x00", maxsplit=1)
            while tree_data:
                mode_and_name, tree_data = tree_data.split(b"\x00", maxsplit=1)
                mode, name = mode_and_name.split()
                entry_type = "tree" if mode.decode('utf-8') == "040000" else "blob"
                curr_sha = tree_data[:20]
                tree_data = tree_data[20:]
                if name_only:
                    print(name.decode("utf-8"))
                else:
                    print(mode.decode("utf-8"), entry_type, curr_sha.hex(), name.decode("utf-8"))

    elif command == "write-tree":
        path = os.getcwd()
        sha = write_tree(path)
        print(sha, end="")

    elif command == "commit-tree":
        tree_sha = sys.argv[2]
        commit_sha = sys.argv[4]
        message = sys.argv[6]

        data = b"".join(
            [
                b"tree %b\n" % tree_sha.encode(),
                b"parent %b\n" % commit_sha.encode(),
                b"timestamp %b\n" % str(int(time.mktime(time.localtime()))).encode(),
                b"author Forquosh <146859576+Forquosh@users.noreply.github.com>\n",
                b"committer Forquosh <146859576+Forquosh@users.noreply.github.com>\n\n",
                message.encode(),
                b"\n",
            ]
        )

        sha = create_object("commit", data)
        print(sha, end="")

    elif command == "clone":
        url = sys.argv[2]
        directory = sys.argv[3]
        parent = Path(directory)

        # Fetch refs
        request = urllib.request.Request(f"{url}/info/refs?service=git-upload-pack")
        with urllib.request.urlopen(request) as f:
            refs = {
                bs[1].decode(): bs[0].decode()
                for bs0 in cast(bytes, f.read()).split(b"\n")
                if (bs1 := bs0[4:])
                   and not bs1.startswith(b"#")
                   and (bs2 := bs1.split(b"\0")[0])
                   and (bs := (bs2[4:] if bs2.endswith(b"HEAD") else bs2).split(b" "))
            }

        # Render references
        for name, sha in refs.items():
            ref_path = parent / ".git" / name
            ref_path.parent.mkdir(parents=True, exist_ok=True)
            ref_path.write_text(sha + "\n")

        # Fetch pack
        body = (
                b"0011command=fetch0001000fno-progress"
                + b"".join(b"0032want " + ref.encode() + b"\n" for ref in refs.values())
                + b"0009done\n0000"
        )
        request = urllib.request.Request(
            f"{url}/git-upload-pack",
            data=body,
            headers={"Git-Protocol": "version=2"},
        )
        with urllib.request.urlopen(request) as f:
            pack_bytes = cast(bytes, f.read())
        pack_lines = []
        while pack_bytes:
            line_length = int(pack_bytes[:4], 16)
            if line_length == 0:
                break
            pack_lines.append(pack_bytes[4:line_length])
            pack_bytes = pack_bytes[line_length:]
        pack_file = b"".join(line[1:] for line in pack_lines[1:])

        def next_size_and_type(bs: bytes) -> Tuple[str, int, bytes]:
            ty = (bs[0] & 0b_0111_0000) >> 4
            match ty:
                case 1:
                    ty = "commit"
                case 2:
                    ty = "tree"
                case 3:
                    ty = "blob"
                case 4:
                    ty = "tag"
                case 6:
                    ty = "ofs_delta"
                case 7:
                    ty = "ref_delta"
                case _:
                    ty = "unknown"

            size = bs[0] & 0b_0000_1111
            index = 1
            off = 4
            while bs[index - 1] & 0b_1000_0000:
                size += (bs[index] & 0b_0111_1111) << off
                off += 7
                index += 1
            return ty, size, bs[index:]

        def next_size(bs: bytes) -> Tuple[int, bytes]:
            size = bs[0] & 0b_0111_1111
            index = 1
            off = 7
            while bs[index - 1] & 0b_1000_0000:
                size += (bs[index] & 0b_0111_1111) << off
                off += 7
                index += 1
            return size, bs[index:]

        # Get objects
        pack_file = pack_file[8:]  # strip header and version
        nr_objects, *_ = struct.unpack("!I", pack_file[:4])
        pack_file = pack_file[4:]
        for _ in range(nr_objects):
            tip, _, pack_file = next_size_and_type(pack_file)
            match tip:
                case "commit" | "tree" | "blob" | "tag":
                    dec = zlib.decompressobj()
                    content = dec.decompress(pack_file)
                    pack_file = dec.unused_data
                    create_object(tip, content, parent)
                case "ref_delta":
                    obj = pack_file[:20].hex()
                    pack_file = pack_file[20:]
                    dec = zlib.decompressobj()
                    content = dec.decompress(pack_file)
                    pack_file = dec.unused_data
                    target_content = b""
                    base_tip, base_content = read_object(obj, parent)
                    # base and output sizes
                    _, content = next_size(content)
                    _, content = next_size(content)
                    while content:
                        is_copy = content[0] & 0b_1000_0000
                        if is_copy:
                            data_ptr = 1
                            offset = 0
                            size = 0
                            for i in range(0, 4):
                                if content[0] & (1 << i):
                                    offset |= content[data_ptr] << (i * 8)
                                    data_ptr += 1
                            for i in range(0, 3):
                                if content[0] & (1 << (4 + i)):
                                    size |= content[data_ptr] << (i * 8)
                                    data_ptr += 1
                            content = content[data_ptr:]
                            target_content += base_content[offset: offset + size]
                        else:
                            size = content[0]
                            append = content[1: size + 1]
                            content = content[size + 1:]
                            target_content += append
                    create_object(base_tip, target_content, parent)
                case _:
                    raise RuntimeError("Not implemented")

        def render_tree(parent: Path, directory: Path, sha: str):
            directory.mkdir(parents=True, exist_ok=True)
            _, tree_data = read_object(sha, parent)
            while tree_data:
                mode, tree_data = tree_data.split(b" ", 1)
                name, tree_data = tree_data.split(b"\0", 1)
                sha = tree_data[:20].hex()
                tree_data = tree_data[20:]
                match mode:
                    case b"40000":
                        render_tree(parent, directory / name.decode(), sha)
                    case b"100644":
                        _, content = read_object(sha, parent)
                        Path(directory / name.decode()).write_bytes(content)
                    case _:
                        raise RuntimeError("Not implemented")

        _, commit = read_object(refs["HEAD"], parent)
        tree_sha = commit[5: 40 + 5].decode()
        render_tree(parent, parent, tree_sha)

    else:
        raise RuntimeError(f"Unknown command #{command}")


if __name__ == "__main__":
    main()
