import sys
import shlex
import os
import socket
import argparse
from pathlib import Path

# Добавляем путь к src в sys.path для импорта модулей
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from PyQt5.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout,
                             QTextEdit, QLineEdit, QPushButton, QWidget, QLabel)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont, QTextCursor

from vfs import VFS, create_default_vfs


class ShellEmulator(QMainWindow):
    # Конструктор класса, принимает опциональные пути к VFS и скрипту
    def __init__(self, vfs_path=None, script_path=None):
        super().__init__()

        # Нормализуем пути - преобразуем относительные пути в абсолютные
        self.vfs_path = self.resolve_path(vfs_path) if vfs_path else None
        self.script_path = self.resolve_path(script_path) if script_path else None

        # Инициализируем VFS
        self.vfs = VFS()

        # СНАЧАЛА настраиваем интерфейс
        self.setWindowTitle(f"Эмулятор - [{os.getlogin()}@{socket.gethostname()}]")
        self.setGeometry(100, 100, 800, 600)
        self.setup_ui()

        # ПОТОМ загружаем VFS (после создания интерфейса)
        self.load_vfs()

        # Инициализация скрипта
        self.script_commands = []
        self.current_script_line = 0
        self.script_timer = QTimer()
        # Связываем сигнал таймера с методом выполнения строки скрипта
        self.script_timer.timeout.connect(self.execute_script_line)

        self.print_startup_info()

        if self.script_path:
            self.load_script()

    def resolve_path(self, path):
        """Преобразует относительный путь в абсолютный"""
        try:
            # Создаем объект Path из переданного пути
            path_obj = Path(path)

            if path_obj.is_absolute():
                return str(path_obj)

            # Получаем директорию, где находится main.py
            script_dir = Path(__file__).parent
            absolute_path = (script_dir / path).resolve()

            print(f"Исходный путь: {path}")  #отладОчка
            print(f"Абсолютный путь: {absolute_path}")
            print(f"Существует: {absolute_path.exists()}")

            # Возвращаем абсолютный путь как строку или исходный путь
            return str(absolute_path)
        except Exception as e:
            print(f"Ошибка в resolve_path: {e}")
            return path

    def load_vfs(self):
        """Загрузка VFS из файла или создание VFS по умолчанию"""
        try:
            if self.vfs_path:
                # Безопасный вывод (на случай, если интерфейс еще не создан)
                # Если output_area существует, используем print_output, иначе обычный print
                safe_print = self.print_output if hasattr(self, 'output_area') else print

                safe_print(f"Пытаемся загрузить VFS из: {self.vfs_path}\n")
                safe_print(f"Файл существует: {Path(self.vfs_path).exists()}\n")

                success = self.vfs.load_from_xml(self.vfs_path)
                if success:
                    safe_print(f"VFS загружена из: {self.vfs_path}\n")
                else:
                    safe_print(f"ОШИБКА: Не удалось загрузить VFS из {self.vfs_path}\n")
                    safe_print("Создана VFS по умолчанию\n")
                    self.vfs = create_default_vfs()
            else:
                safe_print = self.print_output if hasattr(self, 'output_area') else print
                safe_print("VFS не указана, создана VFS по умолчанию\n")
                self.vfs = create_default_vfs()
        except Exception as e:
            safe_print = self.print_output if hasattr(self, 'output_area') else print
            safe_print(f"КРИТИЧЕСКАЯ ОШИБКА при загрузке VFS: {str(e)}\n")
            import traceback
            safe_print(traceback.format_exc())
            self.vfs = create_default_vfs()

    def setup_ui(self):
        """Настройка пользовательского интерфейса"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        # Создаем вертикальный layout для центрального виджета
        layout = QVBoxLayout(central_widget)

        # Область вывода
        self.output_area = QTextEdit()
        self.output_area.setReadOnly(True)
        self.output_area.setFont(QFont("Consolas", 10))
        self.output_area.setStyleSheet("background-color: #1e1e1e; color: #d4d4d4;")
        layout.addWidget(self.output_area)

        # Панель статуса (показывает текущий путь в VFS)
        status_frame = QWidget()
        status_layout = QHBoxLayout(status_frame)
        status_layout.setContentsMargins(5, 2, 5, 2)

        status_label = QLabel("Текущий путь:")
        status_label.setStyleSheet("color: #569cd6; font-weight: bold;")
        status_layout.addWidget(status_label)

        self.path_label = QLabel("/")
        self.path_label.setStyleSheet("color: #ce9178;")
        status_layout.addWidget(self.path_label)
        status_layout.addStretch()

        layout.addWidget(status_frame)

        # Фрейм ввода
        input_frame = QWidget()
        input_layout = QHBoxLayout(input_frame)

        # Метка приглашения
        self.prompt_label = QLabel(">>>")
        self.prompt_label.setStyleSheet("color: #569cd6; font-weight: bold;")
        input_layout.addWidget(self.prompt_label)

        # Поле ввода
        self.input_entry = QLineEdit()
        self.input_entry.setStyleSheet("background-color: #3c3c3c; color: #d4d4d4;")
        self.input_entry.returnPressed.connect(self.execute_command)
        input_layout.addWidget(self.input_entry)

        # Кнопка выполнения
        self.execute_button = QPushButton("Выполнить")
        self.execute_button.clicked.connect(self.execute_command)
        self.execute_button.setStyleSheet("background-color: #0e639c; color: white;")
        input_layout.addWidget(self.execute_button)

        layout.addWidget(input_frame)

        # Устанавливаем фокус на поле ввода
        self.input_entry.setFocus()

    def print_output(self, text):
        """Вывод текста в область вывода"""
        self.output_area.moveCursor(QTextCursor.End)
        self.output_area.insertPlainText(text)
        self.output_area.moveCursor(QTextCursor.End)

    def update_path_display(self):
        """Обновление отображения текущего пути"""
        self.path_label.setText(self.vfs.current_path)

    def print_startup_info(self):
        """Вывод информации о запуске и параметрах конфигурации"""
        self.print_output("Добро пожаловать в эмулятор командной оболочки!\n")
        self.print_output("=" * 60 + "\n")
        self.print_output("КОНФИГУРАЦИЯ ПРИ ЗАПУСКЕ:\n")

        if self.vfs_path:
            self.print_output(f"  VFS путь: {self.vfs_path}\n")
        else:
            self.print_output("  VFS путь: не указан (используется VFS по умолчанию)\n")

        if self.script_path:
            self.print_output(f"  Скрипт: {self.script_path}\n")
        else:
            self.print_output("  Скрипт: не указан\n")

        self.print_output("=" * 60 + "\n")
        self.print_output("Доступные команды: ls, cd, cat, pwd, exit\n")
        self.print_output("Введите команду ниже:\n" + "-" * 40 + "\n")

        # Обновляем отображение пути
        self.update_path_display()

    def parse_command(self, input_text):
        """Парсинг команды с учетом кавычек"""
        try:
            return shlex.split(input_text)
        except ValueError as e:
            return ["error", f"Ошибка парсинга: {str(e)}"]

    def execute_command(self):
        """Выполнение команды из поля ввода"""
        command_text = self.input_entry.text().strip()

        if not command_text:
            return

        # Очищаем поле ввода
        self.input_entry.clear()

        # Выводим введенную команду
        self.print_output(f">>> {command_text}\n")

        # Выполняем команду
        self.process_command(command_text)

    def process_command(self, command_text):
        """Обработка и выполнение команды"""
        parts = self.parse_command(command_text)

        if not parts:
            return

        command = parts[0].lower()
        args = parts[1:]

        # If-else блок с командами
        if command == "exit":
            self.print_output("Завершение работы эмулятора...\n")
            self.close()

        elif command == "ls":
            self.cmd_ls(args)

        elif command == "cd":
            self.cmd_cd(args)

        elif command == "cat":
            self.cmd_cat(args)

        elif command == "pwd":
            self.cmd_pwd(args)

        elif command == "error":
            self.print_output(f"ОШИБКА: {args[0]}\n")

        else:
            self.print_output(f"ОШИБКА: Неизвестная команда '{command}'\n")

        # Обновляем отображение пути после команды
        self.update_path_display()

        # Добавляем разделитель
        self.print_output("-" * 40 + "\n")

    def cmd_ls(self, args):
        """Команда ls - вывод содержимого текущей директории"""
        items = self.vfs.list_current_directory()
        if not items:
            self.print_output("Директория пуста\n")
            return

        for item in sorted(items):
            node_info = self.vfs.get_node_info(item)
            if node_info:
                self.print_output(f"{node_info}\n")

    def cmd_cd(self, args):
        """Команда cd - смена текущей директории"""
        if not args:
            self.print_output("Использование: cd <путь>\n")
            return

        path = args[0]
        success = self.vfs.change_directory(path)

        if success:
            self.print_output(f"Переход в: {self.vfs.current_path}\n")
        else:
            self.print_output(f"ОШИБКА: Директория '{path}' не найдена\n")

    def cmd_cat(self, args):
        """Команда cat - вывод содержимого файла"""
        if not args:
            self.print_output("Использование: cat <имя_файла>\n")
            return

        filename = args[0]
        content = self.vfs.get_file_content(filename)

        if content is not None:
            self.print_output(f"Содержимое файла '{filename}':\n")
            self.print_output(content + "\n")
        else:
            self.print_output(f"ОШИБКА: Файл '{filename}' не найден или не является файлом\n")

    def cmd_pwd(self, args):
        """Команда pwd - вывод текущего пути"""
        self.print_output(f"Текущий путь: {self.vfs.current_path}\n")

    def load_script(self):
        """Загрузка стартового скрипта"""
        try:
            script_file = Path(self.script_path)
            if not script_file.exists():
                self.print_output(f"ОШИБКА: Скрипт '{self.script_path}' не найден\n")
                return False

            with open(script_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            # Фильтруем пустые строки и комментарии
            self.script_commands = []
            for line in lines:
                line = line.strip() # Удаляем пробелы и переносы
                if line and not line.startswith('#'):
                    self.script_commands.append(line)

            self.print_output(f"Загружен скрипт: {self.script_path}\n")
            self.print_output(f"Найдено команд: {len(self.script_commands)}\n")
            self.print_output("Запуск скрипта...\n" + "=" * 40 + "\n")

            # Запускаем выполнение скрипта с задержкой
            QTimer.singleShot(1000, self.start_script_execution)
            return True

        except Exception as e:
            self.print_output(f"ОШИБКА загрузки скрипта: {str(e)}\n")
            return False

    def start_script_execution(self):
        """Начало выполнения скрипта"""
        if self.script_commands:
            self.script_timer.start(500)  # Интервал между командами (мс)

    def execute_script_line(self):
        """Выполнение очередной команды из скрипта"""
        if self.current_script_line >= len(self.script_commands):
            self.script_timer.stop()
            self.print_output("=" * 40 + "\n")
            self.print_output("Выполнение скрипта завершено!\n")
            self.print_output("-" * 40 + "\n")
            return

        command = self.script_commands[self.current_script_line]
        self.current_script_line += 1

        # Выводим команду как будто её ввел пользователь
        self.print_output(f">>> {command}\n")

        # Выполняем команду (пропускаем ошибочные строки)
        try:
            self.process_command(command)
        except Exception as e:
            self.print_output(f"Пропуск ошибочной команды: {str(e)}\n")
            self.print_output("-" * 40 + "\n")


def parse_arguments():
    """Парсинг аргументов командной строки"""
    parser = argparse.ArgumentParser(description='Эмулятор командной оболочки ОС')
    parser.add_argument('--vfs-path', type=str, help='Путь к физическому расположению VFS')
    parser.add_argument('--script', type=str, help='Путь к стартовому скрипту')

    return parser.parse_args()


def main():
    # Парсим аргументы командной строки
    args = parse_arguments()

    # Создаем и запускаем приложение
    app = QApplication(sys.argv)
    # Создаем экземпляр эмулятора с переданными аргументами
    emulator = ShellEmulator(vfs_path=args.vfs_path, script_path=args.script)
    emulator.show() # Показываем кок
    sys.exit(app.exec_())
    # Запускаем главный цикл приложения и выходим когда он завершится



# фсё
if __name__ == "__main__":
    main()
