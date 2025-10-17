import xml.etree.ElementTree as ET
import base64
from pathlib import Path
from typing import Dict, List, Optional, Union


class VFSNode:
    """Базовый класс для узлов VFS"""

    def __init__(self, name: str):
        self.name = name


class VFSFile(VFSNode):
    """Класс файла в VFS"""

    def __init__(self, name: str, content: str = ""):
        super().__init__(name)
        self.content = content
        self._decoded_content = None

    def get_content(self) -> str:
        """Получить декодированное содержимое файла"""
        if self._decoded_content is None and self.content:
            try:
                self._decoded_content = base64.b64decode(self.content).decode('utf-8')
            except:
                self._decoded_content = "[Binary data]"
        return self._decoded_content or ""

    def __str__(self):
        return f"File: {self.name}"


class VFSDirectory(VFSNode):
    """Класс директории в VFS"""

    def __init__(self, name: str, parent=None):
        super().__init__(name)
        self.children: Dict[str, VFSNode] = {}
        self.parent = parent

    def add_child(self, node: VFSNode):
        """Добавить дочерний узел"""
        self.children[node.name] = node
        if isinstance(node, VFSDirectory):
            node.parent = self

    def get_child(self, name: str) -> Optional[VFSNode]:
        """Получить дочерний узел по имени"""
        return self.children.get(name)

    def list_children(self) -> List[str]:
        """Получить список имен дочерних узлов"""
        return list(self.children.keys())

    def __str__(self):
        return f"Directory: {self.name} ({len(self.children)} items)"


class VFS:
    """Виртуальная файловая система"""

    def __init__(self):
        self.root = VFSDirectory("")
        self.current_directory = self.root
        self.current_path = "/"

    def load_from_xml(self, xml_path: str) -> bool:
        """
        Загрузить VFS из XML-файла

        Args:
            xml_path: Путь к XML-файлу

        Returns:
            bool: Успешно ли загружена VFS
        """
        try:
            if not Path(xml_path).exists():
                return False

            tree = ET.parse(xml_path)
            root_element = tree.getroot()

            # Очищаем текущую VFS
            self.root = VFSDirectory("")
            self.current_directory = self.root
            self.current_path = "/"

            # Рекурсивно строим дерево VFS
            self._parse_xml_element(root_element, self.root)
            return True

        except ET.ParseError as e:
            print(f"Ошибка парсинга XML: {e}")
            return False
        except Exception as e:
            print(f"Ошибка загрузки VFS: {e}")
            return False

    def _parse_xml_element(self, element: ET.Element, current_dir: VFSDirectory):
        """Рекурсивный парсинг XML элемента"""
        for child in element:
            if child.tag == 'directory':
                dir_name = child.get('name', 'unnamed')
                new_dir = VFSDirectory(dir_name, current_dir)
                current_dir.add_child(new_dir)
                self._parse_xml_element(child, new_dir)

            elif child.tag == 'file':
                file_name = child.get('name', 'unnamed')
                content = child.text or ""
                new_file = VFSFile(file_name, content)
                current_dir.add_child(new_file)

    def change_directory(self, path: str) -> bool:
        """
        Сменить текущую директорию

        Args:
            path: Путь для перехода

        Returns:
            bool: Успешно ли изменена директория
        """
        if path == "/":
            self.current_directory = self.root
            self.current_path = "/"
            return True

        # Обработка абсолютных и относительных путей
        if path.startswith("/"):
            target_dir = self._resolve_absolute_path(path)
        else:
            target_dir = self._resolve_relative_path(path)

        if target_dir and isinstance(target_dir, VFSDirectory):
            self.current_directory = target_dir
            self.current_path = self._get_full_path(target_dir)
            return True

        return False

    def _resolve_absolute_path(self, path: str) -> Optional[VFSNode]:
        """Разрешить абсолютный путь"""
        parts = [p for p in path.split('/') if p]
        current = self.root

        for part in parts:
            if part == "..":
                if current.parent is not None:
                    current = current.parent
            else:
                if not isinstance(current, VFSDirectory):
                    return None
                current = current.get_child(part)
                if current is None:
                    return None

        return current

    def _resolve_relative_path(self, path: str) -> Optional[VFSNode]:
        """Разрешить относительный путь"""
        parts = [p for p in path.split('/') if p]
        current = self.current_directory

        for part in parts:
            if part == "..":
                if current.parent is not None:
                    current = current.parent
            else:
                if not isinstance(current, VFSDirectory):
                    return None
                current = current.get_child(part)
                if current is None:
                    return None

        return current

    def _get_full_path(self, directory: VFSDirectory) -> str:
        """Получить полный путь для директории"""
        if directory == self.root:
            return "/"

        parts = []
        current = directory

        while current != self.root and current is not None:
            parts.append(current.name)
            current = current.parent

        parts.reverse()
        return "/" + "/".join(parts)

    def list_current_directory(self) -> List[str]:
        """Получить список содержимого текущей директории"""
        return self.current_directory.list_children()

    def get_file_content(self, filename: str) -> Optional[str]:
        """Получить содержимое файла"""
        node = self.current_directory.get_child(filename)
        if isinstance(node, VFSFile):
            return node.get_content()
        return None

    def get_node_info(self, name: str) -> Optional[str]:
        """Получить информацию о узле (файл/директория)"""
        node = self.current_directory.get_child(name)
        if node:
            return str(node)
        return None


def create_default_vfs() -> VFS:
    """Создать VFS по умолчанию"""
    vfs = VFS()

    # Создаем базовую структуру
    home_dir = VFSDirectory("home", vfs.root)
    documents_dir = VFSDirectory("documents", home_dir)
    downloads_dir = VFSDirectory("downloads", home_dir)

    # Создаем файлы
    readme_file = VFSFile("readme.txt", "SGVsbG8gVkZTIEVtdWxhdG9yIQ==")  # "Hello VFS Emulator!"
    note_file = VFSFile("note.txt", " VGhpcyBpcyBhIG5vdGU=")  # "This is a note"

    # Добавляем файлы в директории
    home_dir.add_child(readme_file)
    home_dir.add_child(note_file)
    home_dir.add_child(documents_dir)
    home_dir.add_child(downloads_dir)

    # Добавляем в корневую директорию
    vfs.root.add_child(home_dir)
    vfs.root.add_child(VFSDirectory("tmp", vfs.root))
    vfs.root.add_child(VFSDirectory("var", vfs.root))

    return vfs
