import sys
import os
import chess
import chess.pgn
import time
import random
import json
import queue
from datetime import datetime

try:
    import chess.engine
    HAS_ENGINE = True
except ImportError:
    HAS_ENGINE = False

try:
    import chess.polyglot
    HAS_POLYGLOT = True
except ImportError:
    HAS_POLYGLOT = False

from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5.QtCore import *

# ================= CONFIG =================
BOARD_SIZE = 600
SQ = BOARD_SIZE // 8
# =========================================

class ConsoleWidget(QWidget):
    """Интерактивна конзола за контрол на програмата"""
    
    def __init__(self, main_app):
        super().__init__()
        self.app = main_app
        self.history = []
        self.history_index = 0
        self.command_queue = queue.Queue()
        
        self.init_ui()
        self.setup_commands()
        
    def init_ui(self):
        self.setWindowTitle("PyChess Pro+ Конзола")
        self.resize(700, 400)
        
        layout = QVBoxLayout(self)
        
        # Текстова област за изход
        self.output_text = QTextEdit()
        self.output_text.setReadOnly(True)
        self.output_text.setFont(QFont("Consolas", 10))
        self.output_text.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #f0f0f0;
                border: 1px solid #555;
                border-radius: 3px;
            }
        """)
        layout.addWidget(self.output_text)
        
        # Ред за въвеждане на команди
        input_layout = QHBoxLayout()
        self.prompt_label = QLabel(">>>")
        self.prompt_label.setStyleSheet("color: #00ff00; font-weight: bold;")
        input_layout.addWidget(self.prompt_label)
        
        self.input_line = QLineEdit()
        self.input_line.setFont(QFont("Consolas", 10))
        self.input_line.setStyleSheet("""
            QLineEdit {
                background-color: #2d2d30;
                color: #ffffff;
                border: 1px solid #555;
                border-radius: 3px;
                padding: 5px;
            }
        """)
        self.input_line.returnPressed.connect(self.execute_command)
        input_layout.addWidget(self.input_line)
        
        layout.addLayout(input_layout)
        
        # Статус бар
        self.status_bar = QStatusBar()
        self.status_bar.showMessage(self.tr("Готов. Въведете 'help' за помощ."))
        layout.addWidget(self.status_bar)
        
        # Прихващане на клавишни комбинации
        self.input_line.installEventFilter(self)
        
        self.print_welcome()
        
    def eventFilter(self, obj, event):
        """Прихващане на специални клавиши за история на командите"""
        if obj == self.input_line and event.type() == QEvent.KeyPress:
            if event.key() == Qt.Key_Up:
                self.show_previous_command()
                return True
            elif event.key() == Qt.Key_Down:
                self.show_next_command()
                return True
            elif event.key() == Qt.Key_Tab:
                self.auto_complete()
                return True
        return super().eventFilter(obj, event)
    
    def setup_commands(self):
        """Настройва речник с наличните команди"""
        self.update_command_texts()
    
    def update_command_texts(self):
        """Обновява текстовете на командите според текущия език"""
        language = self.app.language
        
        if language == "bg":
            self.commands = {
                'help': {
                    'func': self.cmd_help,
                    'desc': 'Показва този помощен текст',
                    'usage': 'help [команда]'
                },
                'exit': {
                    'func': self.cmd_exit,
                    'desc': 'Затваря конзолата',
                    'usage': 'exit'
                },
                'clear': {
                    'func': self.cmd_clear,
                    'desc': 'Изчиства екрана на конзолата',
                    'usage': 'clear'
                },
                'newgame': {
                    'func': self.cmd_newgame,
                    'desc': 'Започва нова игра',
                    'usage': 'newgame'
                },
                'quit': {
                    'func': self.cmd_quit,
                    'desc': 'Излиза от програмата',
                    'usage': 'quit'
                },
                'move': {
                    'func': self.cmd_move,
                    'desc': 'Изпълнява ход (пример: move e2e4)',
                    'usage': 'move <ход>'
                },
                'undo': {
                    'func': self.cmd_undo,
                    'desc': 'Отменя последния ход',
                    'usage': 'undo'
                },
                'board': {
                    'func': self.cmd_board,
                    'desc': 'Показва текущата дъска',
                    'usage': 'board'
                },
                'fen': {
                    'func': self.cmd_fen,
                    'desc': 'Показва FEN на текущата позиция',
                    'usage': 'fen'
                },
                'setfen': {
                    'func': self.cmd_setfen,
                    'desc': 'Задава позиция от FEN',
                    'usage': 'setfen <FEN>'
                },
                'eval': {
                    'func': self.cmd_eval,
                    'desc': 'Показва текущата оценка',
                    'usage': 'eval'
                },
                'engine': {
                    'func': self.cmd_engine,
                    'desc': 'Контрол на двигателите',
                    'usage': 'engine [start|stop|status|restart]'
                },
                'mode': {
                    'func': self.cmd_mode,
                    'desc': 'Променя режима на игра',
                    'usage': 'mode [human|engine|analysis]'
                },
                'save': {
                    'func': self.cmd_save,
                    'desc': 'Запазва играта като PGN',
                    'usage': 'save [име_на_файл]'
                },
                'load': {
                    'func': self.cmd_load,
                    'desc': 'Зарежда игра от PGN файл',
                    'usage': 'load <име_на_файл>'
                },
                'history': {
                    'func': self.cmd_history,
                    'desc': 'Показва история на ходовете',
                    'usage': 'history'
                },
                'book': {
                    'func': self.cmd_book,
                    'desc': 'Работа с отваряния',
                    'usage': 'book [load|show|depth|close]'
                },
                'time': {
                    'func': self.cmd_time,
                    'desc': 'Показва оставащото време',
                    'usage': 'time'
                },
                'pause': {
                    'func': self.cmd_pause,
                    'desc': 'Паузира/продължава играта',
                    'usage': 'pause'
                },
                'flip': {
                    'func': self.cmd_flip,
                    'desc': 'Обръща дъската',
                    'usage': 'flip'
                },
                'theme': {
                    'func': self.cmd_theme,
                    'desc': 'Променя темата',
                    'usage': 'theme [dark|light|blue|green|purple|gray]'
                },
                'pieces': {
                    'func': self.cmd_pieces,
                    'desc': 'Зарежда нови фигури',
                    'usage': 'pieces <папка>'
                },
                'language': {
                    'func': self.cmd_language,
                    'desc': 'Променя езика на програмата',
                    'usage': 'language [bg|en]'
                },
                'clock': {
                    'func': self.cmd_clock,
                    'desc': 'Контрол на шахматния часовник',
                    'usage': 'clock [reset|set|add]'
                },
                'hint': {
                    'func': self.cmd_hint,
                    'desc': 'Показва предложение за следващ ход',
                    'usage': 'hint'
                },
                'position': {
                    'func': self.cmd_position,
                    'desc': 'Анализ на позицията',
                    'usage': 'position'
                },
                'export': {
                    'func': self.cmd_export,
                    'desc': 'Експортира играта в различни формати',
                    'usage': 'export [pgn|fen|png]'
                },
                'pgn': {
                    'func': self.cmd_pgn,
                    'desc': 'Работа с PGN бази данни',
                    'usage': 'pgn [open|info|games|next|prev]'
                }
            }
        else:
            self.commands = {
                'help': {
                    'func': self.cmd_help,
                    'desc': 'Shows this help text',
                    'usage': 'help [command]'
                },
                'exit': {
                    'func': self.cmd_exit,
                    'desc': 'Closes the console',
                    'usage': 'exit'
                },
                'clear': {
                    'func': self.cmd_clear,
                    'desc': 'Clears the console screen',
                    'usage': 'clear'
                },
                'newgame': {
                    'func': self.cmd_newgame,
                    'desc': 'Starts a new game',
                    'usage': 'newgame'
                },
                'quit': {
                    'func': self.cmd_quit,
                    'desc': 'Exits the program',
                    'usage': 'quit'
                },
                'move': {
                    'func': self.cmd_move,
                    'desc': 'Makes a move (example: move e2e4)',
                    'usage': 'move <move>'
                },
                'undo': {
                    'func': self.cmd_undo,
                    'desc': 'Undoes the last move',
                    'usage': 'undo'
                },
                'board': {
                    'func': self.cmd_board,
                    'desc': 'Shows the current board',
                    'usage': 'board'
                },
                'fen': {
                    'func': self.cmd_fen,
                    'desc': 'Shows FEN of the current position',
                    'usage': 'fen'
                },
                'setfen': {
                    'func': self.cmd_setfen,
                    'desc': 'Sets position from FEN',
                    'usage': 'setfen <FEN>'
                },
                'eval': {
                    'func': self.cmd_eval,
                    'desc': 'Shows the current evaluation',
                    'usage': 'eval'
                },
                'engine': {
                    'func': self.cmd_engine,
                    'desc': 'Controls the engines',
                    'usage': 'engine [start|stop|status|restart]'
                },
                'mode': {
                    'func': self.cmd_mode,
                    'desc': 'Changes game mode',
                    'usage': 'mode [human|engine|analysis]'
                },
                'save': {
                    'func': self.cmd_save,
                    'desc': 'Saves game as PGN',
                    'usage': 'save [filename]'
                },
                'load': {
                    'func': self.cmd_load,
                    'desc': 'Loads game from PGN file',
                    'usage': 'load <filename>'
                },
                'history': {
                    'func': self.cmd_history,
                    'desc': 'Shows move history',
                    'usage': 'history'
                },
                'book': {
                    'func': self.cmd_book,
                    'desc': 'Works with opening books',
                    'usage': 'book [load|show|depth|close]'
                },
                'time': {
                    'func': self.cmd_time,
                    'desc': 'Shows remaining time',
                    'usage': 'time'
                },
                'pause': {
                    'func': self.cmd_pause,
                    'desc': 'Pauses/resumes the game',
                    'usage': 'pause'
                },
                'flip': {
                    'func': self.cmd_flip,
                    'desc': 'Flips the board',
                    'usage': 'flip'
                },
                'theme': {
                    'func': self.cmd_theme,
                    'desc': 'Changes theme',
                    'usage': 'theme [dark|light|blue|green|purple|gray]'
                },
                'pieces': {
                    'func': self.cmd_pieces,
                    'desc': 'Loads new pieces',
                    'usage': 'pieces <folder>'
                },
                'language': {
                    'func': self.cmd_language,
                    'desc': 'Changes program language',
                    'usage': 'language [bg|en]'
                },
                'clock': {
                    'func': self.cmd_clock,
                    'desc': 'Controls chess clock',
                    'usage': 'clock [reset|set|add]'
                },
                'hint': {
                    'func': self.cmd_hint,
                    'desc': 'Shows suggestion for next move',
                    'usage': 'hint'
                },
                'position': {
                    'func': self.cmd_position,
                    'desc': 'Analyzes the position',
                    'usage': 'position'
                },
                'export': {
                    'func': self.cmd_export,
                    'desc': 'Exports game in different formats',
                    'usage': 'export [pgn|fen|png]'
                },
                'pgn': {
                    'func': self.cmd_pgn,
                    'desc': 'Works with PGN databases',
                    'usage': 'pgn [open|info|games|next|prev]'
                }
            }
    
    def print_welcome(self):
        """Показва начално съобщение"""
        language = self.app.language
        
        if language == "bg":
            welcome = """
╔══════════════════════════════════════════════════════════════╗
║                  PyChess Pro+ Конзола v1.0                   ║
║                Въведете 'help' за списък с команди           ║
║            Ctrl+` за показване/скриване на конзолата         ║
╚══════════════════════════════════════════════════════════════╝
        """
        else:
            welcome = """
╔══════════════════════════════════════════════════════════════╗
║                  PyChess Pro+ Console v1.0                   ║
║               Enter 'help' for command list                  ║
║            Ctrl+` to show/hide console                       ║
╚══════════════════════════════════════════════════════════════╝
        """
        self.print_text(welcome, "system")
    
    def print_text(self, text, msg_type="normal"):
        """Отпечатва текст в конзолата с цвят според типа"""
        if msg_type == "system":
            color = "#00ffff"
        elif msg_type == "error":
            color = "#ff5555"
        elif msg_type == "success":
            color = "#55ff55"
        elif msg_type == "warning":
            color = "#ffff55"
        elif msg_type == "info":
            color = "#55ffff"
        else:
            color = "#f0f0f0"
        
        self.output_text.moveCursor(QTextCursor.End)
        self.output_text.setTextColor(QColor(color))
        self.output_text.insertPlainText(text + "\n")
        self.output_text.moveCursor(QTextCursor.End)
    
    def execute_command(self):
        """Изпълнява въведената команда"""
        command = self.input_line.text().strip()
        self.input_line.clear()
        
        if not command:
            return
        
        # Добавяне в историята
        self.history.append(command)
        self.history_index = len(self.history)
        
        # Показване на командата в конзолата
        self.print_text(f">>> {command}", "info")
        
        # Разделяне на командата и аргументите
        parts = command.split()
        cmd_name = parts[0].lower() if parts else ""
        args = parts[1:] if len(parts) > 1 else []
        
        # Проверка дали командата съществува
        if cmd_name in self.commands:
            try:
                # Изпълняваме командата в основната нишка
                QMetaObject.invokeMethod(self, "execute_in_main_thread", 
                                        Qt.QueuedConnection,
                                        Q_ARG(str, cmd_name),
                                        Q_ARG(list, args))
            except Exception as e:
                self.print_text(f"Грешка при изпълнение: {str(e)}" if self.app.language == "bg" else f"Execution error: {str(e)}", "error")
        else:
            error_msg = f"Неразпозната команда: {cmd_name}. Въведете 'help' за списък." if self.app.language == "bg" else f"Unknown command: {cmd_name}. Enter 'help' for list."
            self.print_text(error_msg, "error")
    
    @pyqtSlot(str, list)
    def execute_in_main_thread(self, cmd_name, args):
        """Изпълнява командата в основната GUI нишка"""
        try:
            self.commands[cmd_name]['func'](args)
        except Exception as e:
            self.print_text(f"Грешка: {str(e)}" if self.app.language == "bg" else f"Error: {str(e)}", "error")
    
    def show_previous_command(self):
        """Показва предишна команда от историята"""
        if self.history and self.history_index > 0:
            self.history_index -= 1
            self.input_line.setText(self.history[self.history_index])
            self.input_line.end(False)
    
    def show_next_command(self):
        """Показва следваща команда от историята"""
        if self.history and self.history_index < len(self.history) - 1:
            self.history_index += 1
            self.input_line.setText(self.history[self.history_index])
            self.input_line.end(False)
        elif self.history and self.history_index == len(self.history) - 1:
            self.history_index = len(self.history)
            self.input_line.clear()
    
    def auto_complete(self):
        """Опитва да допълни текущата команда"""
        current = self.input_line.text().strip()
        if not current:
            return
        
        matches = [cmd for cmd in self.commands.keys() if cmd.startswith(current)]
        if len(matches) == 1:
            self.input_line.setText(matches[0] + " ")
            self.input_line.end(False)
        elif len(matches) > 1:
            info_msg = "Възможни команди: " if self.app.language == "bg" else "Possible commands: "
            self.print_text(info_msg + ", ".join(matches), "info")
    
    # ================= КОМАНДИ =================
    
    def cmd_help(self, args):
        """Показва помощен текст"""
        language = self.app.language
        
        if args:
            cmd = args[0].lower()
            if cmd in self.commands:
                if language == "bg":
                    help_text = f"""
Команда: {cmd}
Описание: {self.commands[cmd]['desc']}
Употреба: {self.commands[cmd]['usage']}
                    """
                else:
                    help_text = f"""
Command: {cmd}
Description: {self.commands[cmd]['desc']}
Usage: {self.commands[cmd]['usage']}
                    """
                self.print_text(help_text, "system")
            else:
                error_msg = f"Няма такава команда: {cmd}" if language == "bg" else f"No such command: {cmd}"
                self.print_text(error_msg, "error")
        else:
            if language == "bg":
                help_text = """
╔══════════════════════════════════════════════════════════════╗
║                      НАЛИЧНИ КОМАНДИ                         ║
╠══════════════════════════════════════════════════════════════╣
                """
                
                # Групираме командите по категории
                categories = {
                    'Игра': ['newgame', 'move', 'undo', 'pause', 'time', 'history'],
                    'Позиция': ['board', 'fen', 'setfen', 'eval', 'flip', 'position'],
                    'Двигател': ['engine', 'mode', 'hint'],
                    'Файлове': ['save', 'load', 'export', 'pgn'],
                    'Отваряния': ['book'],
                    'Настройки': ['theme', 'pieces', 'language'],
                    'Система': ['help', 'clear', 'exit', 'quit']
                }
                
                for category, cmds in categories.items():
                    help_text += f"\n║ {category:^58} ║\n"
                    help_text += "╠══════════════════════════════════════════════════════════════╣\n"
                    for cmd in cmds:
                        if cmd in self.commands:
                            help_text += f"║ {cmd:15} - {self.commands[cmd]['desc']:40} ║\n"
                
                help_text += "╚══════════════════════════════════════════════════════════════╝\n"
                help_text += "\nЗа подробна информация за команда: help <име_на_команда>"
            else:
                help_text = """
╔══════════════════════════════════════════════════════════════╗
║                      AVAILABLE COMMANDS                      ║
╠══════════════════════════════════════════════════════════════╣
                """
                
                # Групираме командите по категории
                categories = {
                    'Game': ['newgame', 'move', 'undo', 'pause', 'time', 'history'],
                    'Position': ['board', 'fen', 'setfen', 'eval', 'flip', 'position'],
                    'Engine': ['engine', 'mode', 'hint'],
                    'Files': ['save', 'load', 'export', 'pgn'],
                    'Opening': ['book'],
                    'Settings': ['theme', 'pieces', 'language'],
                    'System': ['help', 'clear', 'exit', 'quit']
                }
                
                for category, cmds in categories.items():
                    help_text += f"\n║ {category:^58} ║\n"
                    help_text += "╠══════════════════════════════════════════════════════════════╣\n"
                    for cmd in cmds:
                        if cmd in self.commands:
                            help_text += f"║ {cmd:15} - {self.commands[cmd]['desc']:40} ║\n"
                
                help_text += "╚══════════════════════════════════════════════════════════════╝\n"
                help_text += "\nFor detailed command info: help <command_name>"
            
            self.print_text(help_text, "system")
    
    def cmd_exit(self, args):
        """Затваря конзолата"""
        self.hide()
    
    def cmd_clear(self, args):
        """Изчиства екрана"""
        self.output_text.clear()
        self.print_welcome()
    
    def cmd_newgame(self, args):
        """Започва нова игра"""
        self.app.new_game()
        success_msg = "Нова игра започната" if self.app.language == "bg" else "New game started"
        self.print_text(success_msg, "success")
    
    def cmd_quit(self, args):
        """Излиза от програмата"""
        language = self.app.language
        title = "Изход" if language == "bg" else "Exit"
        message = "Сигурни ли сте, че искате да излезете?" if language == "bg" else "Are you sure you want to exit?"
        reply = QMessageBox.question(self, title, message, QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.app.close()
    
    def cmd_move(self, args):
        """Изпълнява ход"""
        language = self.app.language
        
        if not args:
            usage = "Употреба: move <ход> (пример: move e2e4)" if language == "bg" else "Usage: move <move> (example: move e2e4)"
            self.print_text(usage, "error")
            return
        
        move_str = args[0]
        try:
            # Опитваме се да парснем хода
            move = chess.Move.from_uci(move_str.lower())
            
            # Проверяваме дали ходът е легален
            if move in self.app.game_board.legal_moves:
                # Ако сме в режим човек срещу двигател и е ред на човека
                if not self.app.is_engine_vs_engine and self.app.game_board.turn == self.app.player_color:
                    self.app.human_move(move)
                    success_msg = f"Ход изпълнен: {move_str}" if language == "bg" else f"Move executed: {move_str}"
                    self.print_text(success_msg, "success")
                # Ако сме в режим двигател срещу двигател или анализ
                else:
                    # Правим хода директно
                    self.app.game_board.push(move)
                    self.app.current_board = self.app.game_board
                    self.app.refresh_move_list()
                    self.app.board_w.last_move = move
                    self.app.board_w.update()
                    success_msg = f"Ход изпълнен: {move_str}" if language == "bg" else f"Move executed: {move_str}"
                    self.print_text(success_msg, "success")
            else:
                error_msg = f"Нелегален ход: {move_str}" if language == "bg" else f"Illegal move: {move_str}"
                self.print_text(error_msg, "error")
        except ValueError:
            # Опитваме се с алгебрична нотация
            try:
                move = self.app.game_board.parse_san(move_str)
                if move in self.app.game_board.legal_moves:
                    if not self.app.is_engine_vs_engine and self.app.game_board.turn == self.app.player_color:
                        self.app.human_move(move)
                        success_msg = f"Ход изпълнен: {move_str}" if language == "bg" else f"Move executed: {move_str}"
                        self.print_text(success_msg, "success")
                    else:
                        self.app.game_board.push(move)
                        self.app.current_board = self.app.game_board
                        self.app.refresh_move_list()
                        self.app.board_w.last_move = move
                        self.app.board_w.update()
                        success_msg = f"Ход изпълнен: {move_str}" if language == "bg" else f"Move executed: {move_str}"
                        self.print_text(success_msg, "success")
                else:
                    error_msg = f"Нелегален ход: {move_str}" if language == "bg" else f"Illegal move: {move_str}"
                    self.print_text(error_msg, "error")
            except Exception as e:
                error_msg = f"Грешка при изпълнение на ход: {str(e)}" if language == "bg" else f"Error executing move: {str(e)}"
                self.print_text(error_msg, "error")
    
    def cmd_undo(self, args):
        """Отменя последния ход"""
        language = self.app.language
        
        if len(self.app.game_board.move_stack) > 0:
            self.app.undo_move()
            success_msg = "Последният ход отменен" if language == "bg" else "Last move undone"
            self.print_text(success_msg, "success")
        else:
            warning_msg = "Няма ходове за отмяна" if language == "bg" else "No moves to undo"
            self.print_text(warning_msg, "warning")
    
    def cmd_board(self, args):
        """Показва текущата дъска"""
        language = self.app.language
        
        board_str = str(self.app.current_board)
        title = "Текуща дъска:" if language == "bg" else "Current board:"
        self.print_text(title, "system")
        self.print_text(board_str)
        
        # Показваме и кой е на ход
        if self.app.current_board.turn == chess.WHITE:
            turn = "Бели" if language == "bg" else "White"
        else:
            turn = "Черни" if language == "bg" else "Black"
        turn_msg = f"На ход: {turn}" if language == "bg" else f"To move: {turn}"
        self.print_text(turn_msg, "info")
    
    def cmd_fen(self, args):
        """Показва FEN на текущата позиция"""
        language = self.app.language
        
        fen = self.app.current_board.fen()
        title = "FEN нотация:" if language == "bg" else "FEN notation:"
        self.print_text(title, "system")
        self.print_text(fen)
    
    def cmd_setfen(self, args):
        """Задава позиция от FEN"""
        language = self.app.language
        
        if not args:
            usage = "Употреба: setfen <FEN_нотация>" if language == "bg" else "Usage: setfen <FEN_notation>"
            self.print_text(usage, "error")
            return
        
        fen = " ".join(args)
        try:
            self.app.game_board.set_fen(fen)
            self.app.current_board = self.app.game_board
            
            # КОРЕКЦИЯ: Актуализиране на състоянието на играта
            self.app.stop_engine_thread()
            self.app.is_engine_vs_engine = False
            self.app.player_color = self.app.game_board.turn
            self.app.human_turn = True # ВАЖНО: Разрешаваме ход на човека веднага
            
            # ВАЖНА КОРЕКЦИЯ: Нулиране на селекцията на дъската
            self.app.board_w.selected = None
            self.app.game_chart.clear_chart()
            self.app.board_w.legal_moves_for_selected = []
            
            if hasattr(self.app, 'update_turn_display'):
                self.app.update_turn_display()
            
            # ВАЖНА КОРЕКЦИЯ: Проверка за пешки на промоция при импорт през конзола
            for square in chess.SQUARES:
                piece = self.app.game_board.piece_at(square)
                if piece and piece.piece_type == chess.PAWN:
                    rank = chess.square_rank(square)
                    if (piece.color == chess.WHITE and rank == 7) or (piece.color == chess.BLACK and rank == 0):
                        self.app.game_board.set_piece_at(square, chess.Piece(chess.QUEEN, piece.color))
            
            self.app.move_list.clear()
            self.app.refresh_move_list()
            self.app.board_w.update()
            
            # Премахнато излишното update_book_info, тъй като се вика в refresh_move_list или старт на анализ
            
            # НОВО: Стартиране на анализа веднача след импорт
            if self.app.engine:
                self.app.start_analysis()
                
            success_msg = "Позицията е зададена успешно" if language == "bg" else "Position set successfully"
            self.print_text(success_msg, "success")
        except ValueError as e:
            error_msg = f"Невалиден FEN: {str(e)}" if language == "bg" else f"Invalid FEN: {str(e)}"
            self.print_text(error_msg, "error")
    
    def cmd_eval(self, args):
        """Показва текущата оценка"""
        language = self.app.language
        
        if hasattr(self.app, 'last_eval'):
            if self.app.last_eval is None:
                eval_text = "Оценка: 0.00" if language == "bg" else "Eval: 0.00"
            else:
                eval_value = self.app.last_eval/100
                eval_text = f"Оценка: {eval_value:.2f}" if language == "bg" else f"Eval: {eval_value:.2f}"
            self.print_text(eval_text, "info")
        else:
            warning_msg = "Оценката не е налична" if language == "bg" else "Evaluation not available"
            self.print_text(warning_msg, "warning")
    
    def cmd_engine(self, args):
        """Контрол на двигателите"""
        language = self.app.language
        
        if not args:
            # Показваме статус
            engine1_status = "Зареден" if self.app.engine else "Не е зареден"
            engine2_status = "Зареден" if self.app.engine2 else "Не е зареден"
            
            if language == "bg":
                status_text = f"""
Двигател 1 (Бели): {engine1_status}
Двигател 2 (Черни): {engine2_status}
Режим: {'Двигател срещу двигател' if self.app.is_engine_vs_engine else 'Човек срещу двигател'}
                """
            else:
                engine1_status = "Loaded" if self.app.engine else "Not loaded"
                engine2_status = "Loaded" if self.app.engine2 else "Not loaded"
                status_text = f"""
Engine 1 (White): {engine1_status}
Engine 2 (Black): {engine2_status}
Mode: {'Engine vs Engine' if self.app.is_engine_vs_engine else 'Human vs Engine'}
                """
            self.print_text(status_text, "system")
            return
        
        subcmd = args[0].lower()
        if subcmd == "start":
            if self.app.is_engine_vs_engine:
                self.app.start_engine()
                success_msg = "Двигателите са стартирани" if language == "bg" else "Engines started"
                self.print_text(success_msg, "success")
            else:
                warning_msg = "Трябва да сте в режим двигател срещу двигател" if language == "bg" else "Must be in engine vs engine mode"
                self.print_text(warning_msg, "warning")
        elif subcmd == "stop":
            self.app.stop_engine_thread()
            success_msg = "Двигателите са спрени" if language == "bg" else "Engines stopped"
            self.print_text(success_msg, "success")
        elif subcmd == "status":
            engine1_status = "Работи" if self.app.engine_thinking else "Спрян"
            if language == "bg":
                status_msg = f"Състояние на двигателя: {engine1_status}"
            else:
                engine1_status = "Thinking" if self.app.engine_thinking else "Stopped"
                status_msg = f"Engine status: {engine1_status}"
            self.print_text(status_msg, "info")
        elif subcmd == "restart":
            self.app.restart_engine()
            success_msg = "Двигателите са рестартирани" if language == "bg" else "Engines restarted"
            self.print_text(success_msg, "success")
        else:
            error_msg = "Неразпозната подкоманда. Възможности: start, stop, status, restart" if language == "bg" else "Unknown subcommand. Options: start, stop, status, restart"
            self.print_text(error_msg, "error")
    
    def cmd_mode(self, args):
        """Променя режима на игра"""
        language = self.app.language
        
        if not args:
            if language == "bg":
                current_mode = "Двигател срещу двигател" if self.app.is_engine_vs_engine else "Човек срещу двигател"
                self.print_text(f"Текущ режим: {current_mode}", "info")
            else:
                current_mode = "Engine vs Engine" if self.app.is_engine_vs_engine else "Human vs Engine"
                self.print_text(f"Current mode: {current_mode}", "info")
            return
        
        mode = args[0].lower()
        if mode in ["engine", "e"]:
            self.app.is_engine_vs_engine = True
            self.app.settings.set("game_mode", "engine_vs_engine")
            success_msg = "Режим променен на: Двигател срещу двигател" if language == "bg" else "Mode changed to: Engine vs Engine"
            self.print_text(success_msg, "success")
            self.app.new_game()
        elif mode in ["human", "h"]:
            self.app.is_engine_vs_engine = False
            self.app.settings.set("game_mode", "human_vs_engine")
            success_msg = "Режим променен на: Човек срещу двигател" if language == "bg" else "Mode changed to: Human vs Engine"
            self.print_text(success_msg, "success")
            self.app.new_game()
        elif mode in ["analysis", "a"]:
            info_msg = "Режим на анализ. Използвайте командата 'move' за да анализирате позиции." if language == "bg" else "Analysis mode. Use 'move' command to analyze positions."
            self.print_text(info_msg, "info")
        else:
            error_msg = "Невалиден режим. Възможности: engine, human, analysis" if language == "bg" else "Invalid mode. Options: engine, human, analysis"
            self.print_text(error_msg, "error")
    
    def cmd_save(self, args):
        """Запазва играта като PGN"""
        language = self.app.language
        
        filename = args[0] if args else f"game_{time.strftime('%Y%m%d_%H%M%S')}.pgn"
        
        try:
            game = chess.pgn.Game()
            game.setup(self.app.game_board)
            node = game
            for move in self.app.game_board.move_stack:
                node = node.add_main_variation(move)
            
            with open(filename, "w", encoding="utf-8") as f:
                f.write(str(game))
            
            success_msg = f"Играта е запазена във файл: {filename}" if language == "bg" else f"Game saved to file: {filename}"
            self.print_text(success_msg, "success")
        except Exception as e:
            error_msg = f"Грешка при запазване: {str(e)}" if language == "bg" else f"Error saving: {str(e)}"
            self.print_text(error_msg, "error")
    
    def cmd_load(self, args):
        """Зарежда игра от PGN файл"""
        language = self.app.language
        
        if not args:
            usage = "Употреба: load <име_на_файл>" if language == "bg" else "Usage: load <filename>"
            self.print_text(usage, "error")
            return
        
        filename = args[0]
        try:
            self.app.load_pgn_file(filename)
            success_msg = f"Играта е заредена от файл: {filename}" if self.app.language == "bg" else f"Game loaded from file: {filename}"
            self.print_text(success_msg, "success")
        except Exception as e:
            error_msg = f"Грешка при зареждане: {str(e)}" if language == "bg" else f"Error loading: {str(e)}"
            self.print_text(error_msg, "error")
    
    def cmd_history(self, args):
        """Показва история на ходовете"""
        language = self.app.language
        
        if not self.app.game_board.move_stack:
            info_msg = "Няма направени ходове" if language == "bg" else "No moves made"
            self.print_text(info_msg, "info")
            return
        
        title = "История на ходовете:" if language == "bg" else "Move history:"
        self.print_text(title, "system")
        
        temp_board = chess.Board()
        for i, move in enumerate(self.app.game_board.move_stack):
            move_num = i // 2 + 1
            if i % 2 == 0:  # Бели
                san = temp_board.san(move)
                self.print_text(f"{move_num}. {san}", "info")
            else:  # Черни
                san = temp_board.san(move)
                self.print_text(f"{move_num}... {san}", "info")
            temp_board.push(move)
    
    def cmd_book(self, args):
        """Работа с отваряния"""
        language = self.app.language
        
        if not args:
            # Показваме текущите отваряния
            if self.app.book:
                if language == "bg":
                    self.print_text("Отварянията са заредени", "success")
                else:
                    self.print_text("Book is loaded", "success")
                entries = list(self.app.book.find_all(self.app.game_board))
                if entries:
                    count_msg = f"Намерени {len(entries)} възможни хода:" if language == "bg" else f"Found {len(entries)} possible moves:"
                    self.print_text(count_msg, "info")
                    for entry in entries[:5]:
                        san = self.app.game_board.san(entry.move)
                        weight_msg = f"  {san}: тежест {entry.weight}" if language == "bg" else f"  {san}: weight {entry.weight}"
                        self.print_text(weight_msg)
                else:
                    info_msg = "Няма отваряния за тази позиция" if language == "bg" else "No book moves for this position"
                    self.print_text(info_msg, "info")
            else:
                warning_msg = "Няма заредено отваряне" if language == "bg" else "No book loaded"
                self.print_text(warning_msg, "warning")
            return
        
        subcmd = args[0].lower()
        if subcmd == "load":
            if len(args) > 1:
                book_path = args[1]
                try:
                    if self.app.book:
                        self.app.book.close()
                    self.app.book = chess.polyglot.open_reader(book_path)
                    self.app.settings.set("book_path", book_path)
                    success_msg = f"Отварянето е заредено: {book_path}" if language == "bg" else f"Book loaded: {book_path}"
                    self.print_text(success_msg, "success")
                except Exception as e:
                    error_msg = f"Грешка при зареждане: {str(e)}" if language == "bg" else f"Error loading: {str(e)}"
                    self.print_text(error_msg, "error")
            else:
                usage = "Употреба: book load <път_до_файл>" if language == "bg" else "Usage: book load <file_path>"
                self.print_text(usage, "error")
        elif subcmd == "show":
            entries = list(self.book.find_all(self.app.game_board))
            if entries:
                count_msg = f"Възможни ходове от отварянето ({len(entries)}):" if language == "bg" else f"Possible book moves ({len(entries)}):"
                self.print_text(count_msg, "system")
                for entry in entries:
                    san = self.app.game_board.san(entry.move)
                    weight_msg = f"  {san}: тежест {entry.weight}" if language == "bg" else f"  {san}: weight {entry.weight}"
                    self.print_text(weight_msg)
            else:
                info_msg = "Няма отваряния за тази позиция" if language == "bg" else "No book moves for this position"
                self.print_text(info_msg, "info")
        elif subcmd == "depth":
            if len(args) > 1:
                try:
                    depth = int(args[1])
                    self.app.book_max_depth = depth
                    self.app.settings.set("book_max_depth", depth)
                    success_msg = f"Максимална дълбочина на отваряне зададена на: {depth}" if language == "bg" else f"Max book depth set to: {depth}"
                    self.print_text(success_msg, "success")
                except ValueError:
                    error_msg = "Дълбочината трябва да е число" if language == "bg" else "Depth must be a number"
                    self.print_text(error_msg, "error")
            else:
                info_msg = f"Текуща дълбочина на отваряне: {self.app.book_max_depth}" if language == "bg" else f"Current book depth: {self.app.book_max_depth}"
                self.print_text(info_msg, "info")
        elif subcmd == "close":
            if self.app.book:
                self.app.book.close()
                self.app.book = None
                success_msg = "Отварянето е затворено" if language == "bg" else "Book closed"
                self.print_text(success_msg, "success")
            else:
                warning_msg = "Няма активно отваряне" if language == "bg" else "No active book"
                self.print_text(warning_msg, "warning")
        else:
            error_msg = "Неразпозната подкоманда. Възможности: load, show, depth, close" if language == "bg" else "Unknown subcommand. Options: load, show, depth, close"
            self.print_text(error_msg, "error")
    
    def cmd_time(self, args):
        """Показва оставащото време"""
        white_time = self.app.white_clock.time
        black_time = self.app.black_clock.time
        
        white_min, white_sec = divmod(int(white_time), 60)
        black_min, black_sec = divmod(int(black_time), 60)
        
        if self.app.language == "bg":
            time_text = f"""
Бели: {white_min:02d}:{white_sec:02d}
Черни: {black_min:02d}:{black_sec:02d}
Инкремент: {self.app.increment} сек.
            """
        else:
            time_text = f"""
White: {white_min:02d}:{white_sec:02d}
Black: {black_min:02d}:{black_sec:02d}
Increment: {self.app.increment} sec.
            """
        self.print_text(time_text, "system")
    
    def cmd_pause(self, args):
        """Паузира/продължава играта"""
        language = self.app.language
        
        self.app.toggle_pause()
        if self.app.is_paused:
            status = "паузирана" if language == "bg" else "paused"
        else:
            status = "продължена" if language == "bg" else "resumed"
        status_msg = f"Играта е {status}" if language == "bg" else f"Game {status}"
        self.print_text(status_msg, "success")
    
    def cmd_flip(self, args):
        """Обръща дъската"""
        language = self.app.language
        
        self.app.flip_board()
        success_msg = "Дъската е обърната" if language == "bg" else "Board flipped"
        self.print_text(success_msg, "success")
    
    def cmd_theme(self, args):
        """Променя темата"""
        language = self.app.language
        
        if not args:
            current_theme = self.app.current_theme
            theme_names = {
                'dark_blue': 'Тъмно синя' if language == 'bg' else 'Dark Blue',
                'classic': 'Класическа' if language == 'bg' else 'Classic',
                'green': 'Зелена' if language == 'bg' else 'Green',
                'blue': 'Синя' if language == 'bg' else 'Blue',
                'purple': 'Лилава' if language == 'bg' else 'Purple',
                'gray': 'Сива' if language == 'bg' else 'Gray'
            }
            theme_name = theme_names.get(current_theme, current_theme)
            info_msg = f"Текуща тема: {theme_name}" if language == "bg" else f"Current theme: {theme_name}"
            self.print_text(info_msg, "info")
            return
        
        theme = args[0].lower()
        theme_map = {
            'dark': 'dark_blue',
            'light': 'classic',
            'blue': 'blue',
            'green': 'green',
            'purple': 'purple',
            'gray': 'gray'
        }
        
        if theme in theme_map:
            self.app.change_theme(theme_map[theme])
            theme_names = {
                'dark_blue': 'Тъмно синя' if language == 'bg' else 'Dark Blue',
                'classic': 'Класическа' if language == 'bg' else 'Classic',
                'green': 'Зелена' if language == 'bg' else 'Green',
                'blue': 'Синя' if language == 'bg' else 'Blue',
                'purple': 'Лилава' if language == 'bg' else 'Purple',
                'gray': 'Сива' if language == 'bg' else 'Gray'
            }
            theme_name = theme_names.get(theme_map[theme], theme)
            success_msg = f"Темата е променена на: {theme_name}" if language == "bg" else f"Theme changed to: {theme_name}"
            self.print_text(success_msg, "success")
        else:
            error_msg = "Невалидна тема. Възможности: dark, light, blue, green, purple, gray" if language == "bg" else "Invalid theme. Options: dark, light, blue, green, purple, gray"
            self.print_text(error_msg, "error")
    
    def cmd_pieces(self, args):
        """Зарежда нови фигури"""
        language = self.app.language
        
        if not args:
            usage = "Употреба: pieces <папка_с_фигури>" if language == "bg" else "Usage: pieces <pieces_folder>"
            self.print_text(usage, "error")
            return
        
        folder = args[0]
        if os.path.exists(folder):
            self.app.board_w.load_pieces(folder)
            self.app.board_w.update()
            self.app.settings.set("pieces_folder", folder)
            success_msg = f"Фигурите са заредени от: {folder}" if language == "bg" else f"Pieces loaded from: {folder}"
            self.print_text(success_msg, "success")
        else:
            error_msg = f"Папката не съществува: {folder}" if language == "bg" else f"Folder does not exist: {folder}"
            self.print_text(error_msg, "error")
    
    def cmd_language(self, args):
        """Променя езика на програмата"""
        language = self.app.language
        
        if not args:
            current_lang = "Български" if language == "bg" else "English"
            info_msg = f"Текущ език: {current_lang}" if language == "bg" else f"Current language: {current_lang}"
            self.print_text(info_msg, "info")
            return
        
        lang = args[0].lower()
        if lang in ["bg", "bulgarian", "бг"]:
            self.app.change_language("bg")
            success_msg = "Езикът е променен на български" if language == "bg" else "Language changed to Bulgarian"
            self.print_text(success_msg, "success")
            # Обновяваме текстовете в конзолата
            self.update_command_texts()
            self.print_welcome()
            self.status_bar.showMessage("Готов. Въведете 'help' за помощ.")
        elif lang in ["en", "english", "анг"]:
            self.app.change_language("en")
            success_msg = "Language changed to English" if language == "en" else "Езикът е променен на английски"
            self.print_text(success_msg, "success")
            # Обновяваме текстовете в конзолата
            self.update_command_texts()
            self.print_welcome()
            self.status_bar.showMessage("Ready. Enter 'help' for help.")
        else:
            error_msg = "Невалиден език. Възможности: bg, en" if language == "bg" else "Invalid language. Options: bg, en"
            self.print_text(error_msg, "error")
    
    def cmd_clock(self, args):
        """Контрол на шахматния часовник"""
        language = self.app.language
        
        if not args:
            white_time = self.app.white_clock.time
            black_time = self.app.black_clock.time
            
            white_min, white_sec = divmod(int(white_time), 60)
            black_min, black_sec = divmod(int(black_time), 60)
            
            if language == "bg":
                status_text = f"""
Шахматен часовник:
Бели: {white_min:02d}:{white_sec:02d}
Черни: {black_min:02d}:{black_sec:02d}
Време за игра: {self.app.time_control//60} мин.
Инкремент: {self.app.increment} сек.
                """
            else:
                status_text = f"""
Chess Clock:
White: {white_min:02d}:{white_sec:02d}
Black: {black_min:02d}:{black_sec:02d}
Game time: {self.app.time_control//60} min.
Increment: {self.app.increment} sec.
                """
            self.print_text(status_text, "system")
            return
        
        subcmd = args[0].lower()
        if subcmd == "reset":
            self.app.white_clock.reset(self.app.time_control)
            self.app.black_clock.reset(self.app.time_control)
            success_msg = "Часовникът е нулиран" if language == "bg" else "Clock reset"
            self.print_text(success_msg, "success")
        elif subcmd == "set":
            if len(args) >= 3:
                try:
                    player = args[1].lower()
                    time_str = args[2]
                    
                    if ":" in time_str:
                        parts = time_str.split(":")
                        if len(parts) == 2:
                            minutes = int(parts[0])
                            seconds = int(parts[1])
                            total_seconds = minutes * 60 + seconds
                        else:
                            error_msg = "Невалиден формат на времето. Използвайте MM:SS" if language == "bg" else "Invalid time format. Use MM:SS"
                            self.print_text(error_msg, "error")
                            return
                    else:
                        total_seconds = int(time_str)
                    
                    if player in ["white", "w", "бели", "б"]:
                        self.app.white_clock.time = float(total_seconds)
                        self.app.white_clock.update_text()
                        success_msg = f"Времето на белите е зададено на: {total_seconds//60:02d}:{total_seconds%60:02d}" if language == "bg" else f"White time set to: {total_seconds//60:02d}:{total_seconds%60:02d}"
                        self.print_text(success_msg, "success")
                    elif player in ["black", "b", "черни", "ч"]:
                        self.app.black_clock.time = float(total_seconds)
                        self.app.black_clock.update_text()
                        success_msg = f"Времето на черните е зададено на: {total_seconds//60:02d}:{total_seconds%60:02d}" if language == "bg" else f"Black time set to: {total_seconds//60:02d}:{total_seconds%60:02d}"
                        self.print_text(success_msg, "success")
                    else:
                        error_msg = "Невалиден играч. Възможности: white, black" if language == "bg" else "Invalid player. Options: white, black"
                        self.print_text(error_msg, "error")
                except ValueError:
                    error_msg = "Невалидно време" if language == "bg" else "Invalid time"
                    self.print_text(error_msg, "error")
            else:
                usage = "Употреба: clock set <играч> <време>" if language == "bg" else "Usage: clock set <player> <time>"
                self.print_text(usage, "error")
        elif subcmd == "add":
            if len(args) >= 3:
                try:
                    player = args[1].lower()
                    seconds = int(args[2])
                    
                    if player in ["white", "w", "бели", "б"]:
                        self.app.white_clock.time += seconds
                        self.app.white_clock.update_text()
                        success_msg = f"Добавени {seconds} секунди към белите" if language == "bg" else f"Added {seconds} seconds to white"
                        self.print_text(success_msg, "success")
                    elif player in ["black", "b", "черни", "ч"]:
                        self.app.black_clock.time += seconds
                        self.app.black_clock.update_text()
                        success_msg = f"Добавени {seconds} секунди към черните" if language == "bg" else f"Added {seconds} seconds to black"
                        self.print_text(success_msg, "success")
                    else:
                        error_msg = "Невалиден играч. Възможности: white, black" if language == "bg" else "Invalid player. Options: white, black"
                        self.print_text(error_msg, "error")
                except ValueError:
                    error_msg = "Невалиден брой секунди" if language == "bg" else "Invalid number of seconds"
                    self.print_text(error_msg, "error")
            else:
                usage = "Употреба: clock add <играч> <секунди>" if language == "bg" else "Usage: clock add <player> <seconds>"
                self.print_text(usage, "error")
        else:
            error_msg = "Неразпозната подкоманда. Възможности: reset, set, add" if language == "bg" else "Unknown subcommand. Options: reset, set, add"
            self.print_text(error_msg, "error")
    
    def cmd_hint(self, args):
        """Показва предложение за следващ ход"""
        language = self.app.language
        
        if self.app.board_w.best_engine_move:
            move = self.app.board_w.best_engine_move
            san = self.app.current_board.san(move)
            uci = move.uci()
            
            if language == "bg":
                hint_text = f"""
Съвет за следващ ход:
Алгебрична нотация: {san}
UCI нотация: {uci}
                """
            else:
                hint_text = f"""
Next move suggestion:
Algebraic notation: {san}
UCI notation: {uci}
                """
            self.print_text(hint_text, "info")
        else:
            if self.app.analysis_thread and self.app.analysis_thread.isRunning():
                info_msg = "Двигателят все още анализира. Изчакайте..." if language == "bg" else "Engine is still analyzing. Wait..."
                self.print_text(info_msg, "info")
            else:
                warning_msg = "Няма налична информация за следващ ход" if language == "bg" else "No next move information available"
                self.print_text(warning_msg, "warning")
    
    def cmd_position(self, args):
        """Анализ на позицията"""
        language = self.app.language
        
        board = self.app.current_board
        
        # Брой фигури
        white_pieces = sum([len(board.pieces(pt, chess.WHITE)) for pt in range(1, 7)])
        black_pieces = sum([len(board.pieces(pt, chess.BLACK)) for pt in range(1, 7)])
        
        # Легални ходове
        temp_board = board.copy()
        temp_board.turn = chess.WHITE
        white_legal_moves = temp_board.legal_moves.count()
        temp_board.turn = chess.BLACK
        black_legal_moves = temp_board.legal_moves.count()
        
        # Контрол на центъра
        center_squares = [chess.E4, chess.D4, chess.E5, chess.D5]
        white_center_control = sum(1 for sq in center_squares if board.is_attacked_by(chess.WHITE, sq))
        black_center_control = sum(1 for sq in center_squares if board.is_attacked_by(chess.BLACK, sq))
        
        # Шах ли е?
        is_check = board.is_check()
        
        if language == "bg":
            position_text = f"""
Анализ на позицията:
========================
Фигури:
  Бели: {white_pieces}
  Черни: {black_pieces}

Легални ходове:
  Бели: {white_legal_moves}
  Черни: {black_legal_moves}

Контрол на центъра (4 квадрата):
  Бели: {white_center_control}/4
  Черни: {black_center_control}/4

Състояние:
  {'ШАХ!' if is_check else 'Няма шах'}
  {'Равенство' if board.is_game_over() and board.result() == '1/2-1/2' else 'Играта продължава'}
            """
        else:
            position_text = f"""
Position Analysis:
========================
Pieces:
  White: {white_pieces}
  Black: {black_pieces}

Legal moves:
  White: {white_legal_moves}
  Black: {black_legal_moves}

Center control (4 squares):
  White: {white_center_control}/4
  Black: {black_center_control}/4

Status:
  {'CHECK!' if is_check else 'No check'}
  {'Draw' if board.is_game_over() and board.result() == '1/2-1/2' else 'Game continues'}
            """
        
        self.print_text(position_text, "system")
    
    def cmd_export(self, args):
        """Експортира играта в различни формати"""
        language = self.app.language
        
        if not args:
            usage = "Употреба: export [pgn|fen|png]" if language == "bg" else "Usage: export [pgn|fen|png]"
            self.print_text(usage, "error")
            return
        
        format_type = args[0].lower()
        
        if format_type == "pgn":
            filename = args[1] if len(args) > 1 else f"game_{time.strftime('%Y%m%d_%H%M%S')}.pgn"
            try:
                game = chess.pgn.Game()
                game.setup(self.app.game_board)
                node = game
                for move in self.app.game_board.move_stack:
                    node = node.add_main_variation(move)
                
                with open(filename, "w", encoding="utf-8") as f:
                    f.write(str(game))
                
                success_msg = f"Играта е експортирана като PGN: {filename}" if language == "bg" else f"Game exported as PGN: {filename}"
                self.print_text(success_msg, "success")
            except Exception as e:
                error_msg = f"Грешка при експортиране на PGN: {str(e)}" if language == "bg" else f"Error exporting PGN: {str(e)}"
                self.print_text(error_msg, "error")
        
        elif format_type == "fen":
            fen = self.app.current_board.fen()
            self.print_text("FEN нотация:" if language == "bg" else "FEN notation:", "system")
            self.print_text(fen)
            
            # Копиране в клипборда
            clipboard = QApplication.clipboard()
            clipboard.setText(fen)
            info_msg = "FEN е копиран в клипборда" if language == "bg" else "FEN copied to clipboard"
            self.print_text(info_msg, "info")
        
        elif format_type == "png":
            warning_msg = "Експортиране като PNG все още не е имплементирано" if language == "bg" else "Export as PNG not yet implemented"
            self.print_text(warning_msg, "warning")
        
        else:
            error_msg = "Невалиден формат. Възможности: pgn, fen, png" if language == "bg" else "Invalid format. Options: pgn, fen, png"
            self.print_text(error_msg, "error")
    
    def cmd_pgn(self, args):
        """Работа с PGN бази данни"""
        language = self.app.language
        
        if not args:
            if self.app.pgn_file_path:
                file_info = f"Отворен PGN файл: {self.app.pgn_file_path}" if language == "bg" else f"Open PGN file: {self.app.pgn_file_path}"
                games_info = f"Брой партии: {len(self.app.pgn_games)}" if language == "bg" else f"Number of games: {len(self.app.pgn_games)}"
                current_info = f"Текуща партия: {self.app.current_pgn_index + 1}/{len(self.app.pgn_games)}" if language == "bg" else f"Current game: {self.app.current_pgn_index + 1}/{len(self.app.pgn_games)}"
                
                info_text = f"""
{file_info}
{games_info}
{current_info}
                """
                self.print_text(info_text, "info")
            else:
                info_msg = "Няма отворен PGN файл" if language == "bg" else "No PGN file open"
                self.print_text(info_msg, "info")
            return
        
        subcmd = args[0].lower()
        if subcmd == "open":
            self.app.load_pgn()
            if self.app.pgn_file_path:
                success_msg = f"PGN файл отворен: {self.app.pgn_file_path}" if language == "bg" else f"PGN file opened: {self.app.pgn_file_path}"
                self.print_text(success_msg, "success")
        elif subcmd == "info":
            if self.app.pgn_file_path and self.app.pgn_games:
                game = self.app.pgn_games[self.app.current_pgn_index]
                info = self.app.get_pgn_game_info(game)
                self.print_text(info, "system")
            else:
                warning_msg = "Няма отворен PGN файл" if language == "bg" else "No PGN file open"
                self.print_text(warning_msg, "warning")
        elif subcmd == "games":
            if self.app.pgn_file_path and self.app.pgn_games:
                if len(self.app.pgn_games) > 0:
                    count_msg = f"Брой партии в базата: {len(self.app.pgn_games)}" if language == "bg" else f"Games in database: {len(self.app.pgn_games)}"
                    self.print_text(count_msg, "info")
                    for i, game in enumerate(self.app.pgn_games[:10]):
                        event = game.headers.get("Event", "N/A")
                        white = game.headers.get("White", "N/A")
                        black = game.headers.get("Black", "N/A")
                        result = game.headers.get("Result", "*")
                        game_info = f"{i+1}. {white} vs {black} ({result}) - {event}"
                        self.print_text(game_info)
                else:
                    info_msg = "Няма партии в PGN файла" if language == "bg" else "No games in PGN file"
                    self.print_text(info_msg, "info")
            else:
                warning_msg = "Няма отворен PGN файл" if language == "bg" else "No PGN file open"
                self.print_text(warning_msg, "warning")
        elif subcmd == "next":
            if self.app.pgn_file_path and self.app.pgn_games:
                if self.app.current_pgn_index < len(self.app.pgn_games) - 1:
                    self.app.current_pgn_index += 1
                    self.app.load_pgn_game(self.app.current_pgn_index)
                    success_msg = f"Заредена партия {self.app.current_pgn_index + 1}/{len(self.app.pgn_games)}" if language == "bg" else f"Loaded game {self.app.current_pgn_index + 1}/{len(self.app.pgn_games)}"
                    self.print_text(success_msg, "success")
                else:
                    info_msg = "Това е последната партия" if language == "bg" else "This is the last game"
                    self.print_text(info_msg, "info")
            else:
                warning_msg = "Няма отворен PGN файл" if language == "bg" else "No PGN file open"
                self.print_text(warning_msg, "warning")
        elif subcmd == "prev":
            if self.app.pgn_file_path and self.app.pgn_games:
                if self.app.current_pgn_index > 0:
                    self.app.current_pgn_index -= 1
                    self.app.load_pgn_game(self.app.current_pgn_index)
                    success_msg = f"Заредена партия {self.app.current_pgn_index + 1}/{len(self.app.pgn_games)}" if language == "bg" else f"Loaded game {self.app.current_pgn_index + 1}/{len(self.app.pgn_games)}"
                    self.print_text(success_msg, "success")
                else:
                    info_msg = "Това е първата партия" if language == "bg" else "This is the first game"
                    self.print_text(info_msg, "info")
            else:
                warning_msg = "Няма отворен PGN файл" if language == "bg" else "No PGN file open"
                self.print_text(warning_msg, "warning")
        else:
            error_msg = "Неразпозната подкоманда. Възможности: open, info, games, next, prev" if language == "bg" else "Unknown subcommand. Options: open, info, games, next, prev"
            self.print_text(error_msg, "error")


class EngineThread(QThread):
    info = pyqtSignal(object)
    bestmove = pyqtSignal(object)
    error = pyqtSignal(str)

    def __init__(self, engine, board, time_control, increment=0, is_analysis=False):
        super().__init__()
        self.engine = engine
        self.board = board.copy()
        self.time_control = time_control
        self.increment = increment
        self.is_analysis = is_analysis
        self._stop_requested = False

    def run(self):
        if not HAS_ENGINE or not self.engine:
            return
        try:
            if self.is_analysis:
                # БЕЗКРАЕН АНАЛИЗ - без ограничение на дълбочина или време
                with self.engine.analysis(self.board, chess.engine.Limit()) as analysis:
                    for info in analysis:
                        if self._stop_requested:
                            break
                        self.info.emit(info)
            else:
                if self.time_control > 0:
                    remaining_time = self.time_control
                    moves_to_go = 40
                    
                    time_for_move = remaining_time / moves_to_go + self.increment
                    min_time = 0.1
                    time_for_move = max(time_for_move, min_time)
                    max_time = remaining_time * 0.3
                    time_for_move = min(time_for_move, max_time)
                    
                    if remaining_time < 10:
                        limit = chess.engine.Limit(time=time_for_move)
                    else:
                        limit = chess.engine.Limit(time=time_for_move)
                else:
                    limit = chess.engine.Limit(depth=15)
                
                if self.board.is_game_over():
                    return
                
                try:
                    with self.engine.analysis(self.board, limit) as analysis:
                        for info in analysis:
                            if self._stop_requested:
                                break
                            self.info.emit(info)
                except Exception:
                    if not self._stop_requested:
                        return
                
                if not self._stop_requested:
                    try:
                        result = self.engine.play(self.board, limit)
                        if result and result.move:
                            self.bestmove.emit(result.move)
                    except Exception:
                        if not self._stop_requested:
                            pass
        except chess.engine.EngineTerminatedError:
            if not self._stop_requested:
                self.error.emit("Engine terminated")
        except Exception:
            if not self._stop_requested:
                self.error.emit("Engine error")

    def stop(self):
        self._stop_requested = True
        self.requestInterruption()
        self.engine = None
        time.sleep(0.1)


class PGNLoaderThread(QThread):
    """Тред за зареждане на PGN файлове с прогрес"""
    progress = pyqtSignal(int)
    games_loaded = pyqtSignal(list)
    error = pyqtSignal(str)
    
    def __init__(self, file_path):
        super().__init__()
        self.file_path = file_path
    
    def run(self):
        try:
            games = []
            
            # Отваряме файла и преброяваме общия брой редове за прогрес
            with open(self.file_path, 'r', encoding='utf-8', errors='ignore') as f:
                total_lines = sum(1 for _ in f)
            
            # Зареждаме игрите с прогрес
            with open(self.file_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines_read = 0
                while True:
                    # Използваме read_game с файловия обект
                    try:
                        game = chess.pgn.read_game(f)
                        if game is None:
                            break
                        games.append(game)
                        
                        # Актуализираме прогреса
                        lines_read = f.tell()
                        if total_lines > 0:
                            progress = int((lines_read / total_lines) * 100)
                            self.progress.emit(min(progress, 99))
                    except Exception as e:
                        print(f"Грешка при парсване на игра: {e}")
                        continue
            
            self.progress.emit(100)
            self.games_loaded.emit(games)
            
        except Exception as e:
            self.error.emit(f"Грешка при зареждане на PGN: {str(e)}")


class VerticalEvalBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(20)
        self.current_score = 0.0
        self.target_score = 0.0
        self.setStyleSheet("border: 1px solid #555; background: #333;")
        
        self.anim_timer = QTimer()
        self.anim_timer.timeout.connect(self.animate)
        self.anim_timer.start(16)

    def set_score(self, score_cp):
        if score_cp is None: 
            self.target_score = 0
            return
        if score_cp > 1000: self.target_score = 1000
        elif score_cp < -1000: self.target_score = -1000
        else: self.target_score = score_cp

    def animate(self):
        diff = self.target_score - self.current_score
        if abs(diff) > 0.5:
            self.current_score += diff * 0.1
            self.update()
        else:
            self.current_score = self.target_score

    def paintEvent(self, e):
        qp = QPainter(self)
        qp.setRenderHint(QPainter.Antialiasing)
        w = self.width()
        h = self.height()
        
        percent = 50 - (self.current_score / 20.0)
        percent = max(0, min(100, percent))
        
        white_height = int(h * percent / 100)
        qp.fillRect(0, 0, w, white_height, QColor(255, 255, 255))
        
        qp.fillRect(0, white_height, w, h - white_height, QColor(30, 30, 30))
        
        center_y = h // 2
        qp.setPen(QPen(QColor(100, 100, 100), 2))
        qp.drawLine(0, center_y, w, center_y)


class PromotionDialog(QDialog):
    def __init__(self, color, language, parent=None):
        super().__init__(parent)
        self.language = language
        self.setWindowTitle("Промоция на пешка" if language == "bg" else "Promote Pawn")
        self.color_str = "w" if color == chess.WHITE else "b"
        self.result = chess.QUEEN
        self.parent_widget = parent
        self.init_ui()

    def init_ui(self):
        layout = QHBoxLayout(self)
        btn_size = 60
        pieces_map = {chess.QUEEN: "q", chess.ROOK: "r", chess.BISHOP: "b", chess.KNIGHT: "n"}
        
        # Първо пробваме да заредим от родителския widget
        pieces_folder = "pieces/"
        if self.parent_widget and hasattr(self.parent_widget, 'app'):
            if hasattr(self.parent_widget.app, 'settings'):
                pieces_folder = self.parent_widget.app.settings.get("pieces_folder", "pieces/")
        
        for p_type, symbol in pieces_map.items():
            btn = QPushButton()
            btn.setFixedSize(btn_size, btn_size)
            
            possible_paths = [
                os.path.join(pieces_folder, f"{self.color_str}{symbol}.png"),
                f"pieces/{self.color_str}{symbol}.png",
                os.path.join("pieces", f"{self.color_str}{symbol}.png")
            ]
            
            icon_found = False
            for ico_path in possible_paths:
                if os.path.exists(ico_path):
                    btn.setIcon(QIcon(ico_path))
                    btn.setIconSize(QSize(50, 50))
                    icon_found = True
                    break
            
            if not icon_found:
                btn.setText(symbol.upper())
                btn.setFont(QFont("Arial", 20, QFont.Bold))
            
            btn.clicked.connect(lambda checked, pt=p_type: self.set_result(pt))
            layout.addWidget(btn)
            
        # Настройки на прозореца
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setModal(True)
        self.setAttribute(Qt.WA_DeleteOnClose)
        
    def set_result(self, p_type):
        self.result = p_type
        self.accept()
        
    def keyPressEvent(self, event):
        """Прихващане на клавиш Enter за по-бърз избор (по подразбиране дама)"""
        if event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter:
            self.accept()
        elif event.key() == Qt.Key_Escape:
            self.reject()
        else:
            super().keyPressEvent(event)


class BoardWidget(QWidget):
    human_move = pyqtSignal(object)
    
    def __init__(self, main_app):
        super().__init__()
        self.app = main_app
        self.pieces = {}
        self.selected = None
        self.last_move = None
        self.legal_moves_for_selected = []
        self.best_engine_move = None
        self.flipped = False
        self.show_engine_arrows = True
        self.setFixedSize(BOARD_SIZE, BOARD_SIZE)
        self.setStyleSheet("border: 2px solid #555;")
        
        self.promotion_dialog_open = False
        self.promotion_target = None
        
        self.generate_standard_text_pieces()

    def generate_standard_text_pieces(self):
        unicode_pieces = {
            'wp': '♙', 'wn': '♘', 'wb': '♗', 'wr': '♖', 'wq': '♕', 'wk': '♔',
            'bp': '♟', 'bn': '♞', 'bb': '♝', 'br': '♜', 'bq': '♛', 'bk': '♚'
        }
        
        font_size = int(SQ * 0.6)
        font = QFont("Segoe UI Symbol", font_size)
        font.setBold(True)
        
        for piece_key, symbol in unicode_pieces.items():
            pm = QPixmap(SQ, SQ)
            pm.fill(Qt.transparent)
            qp = QPainter(pm)
            qp.setRenderHint(QPainter.Antialiasing)
            
            if piece_key.startswith('w'):
                if self.app.dark_theme_enabled:
                    qp.setPen(QColor(255, 255, 255))
                else:
                    qp.setPen(QColor(0, 0, 0))
            else:
                if self.app.dark_theme_enabled:
                    qp.setPen(QColor(220, 220, 220))
                else:
                    qp.setPen(QColor(50, 50, 50))
            
            qp.setFont(font)
            qp.drawText(pm.rect(), Qt.AlignCenter, symbol)
            qp.end()
            self.pieces[piece_key] = pm

    def load_pieces(self, folder):
        if not os.path.exists(folder):
            return
        
        png_files = [f for f in os.listdir(folder) if f.endswith('.png')]
        if not png_files:
            return
        
        self.pieces.clear()
        for name in ["wp","wn","wb","wr","wq","wk",
                     "bp","bn","bb","br","bq","bk"]:
            path = os.path.join(folder, name + ".png")
            if os.path.exists(path):
                self.pieces[name] = QPixmap(path).scaled(
                    SQ, SQ, Qt.KeepAspectRatio, Qt.SmoothTransformation
                )
        
        if not self.pieces:
            self.generate_standard_text_pieces()
        
        self.update()

    def paintEvent(self, e):
        qp = QPainter(self)
        qp.setRenderHint(QPainter.Antialiasing)

        light = self.app.light_square_color
        dark = self.app.dark_square_color

        for r in range(8):
            for c in range(8):
                if self.flipped:
                    col, row = (7-c)*SQ, (7-r)*SQ
                else:
                    col, row = c*SQ, r*SQ
                    
                if (r + c) % 2 == 0:
                    qp.fillRect(col, row, SQ, SQ, light)
                else:
                    qp.fillRect(col, row, SQ, SQ, dark)

        if self.last_move:
            f1, r1 = chess.square_file(self.last_move.from_square), 7 - chess.square_rank(self.last_move.from_square)
            f2, r2 = chess.square_file(self.last_move.to_square), 7 - chess.square_rank(self.last_move.to_square)
            
            if self.flipped:
                f1, r1 = 7-f1, 7-r1
                f2, r2 = 7-f2, 7-r2
            
            col1, row1 = f1*SQ, r1*SQ
            col2, row2 = f2*SQ, r2*SQ
                
            for col, row in [(col1, row1), (col2, row2)]:
                qp.fillRect(col, row, SQ, SQ, QColor(255, 255, 0, 100) if self.app.dark_theme_enabled else QColor(246, 246, 105, 160))

        if self.selected:
            fs, rs = chess.square_file(self.selected), 7 - chess.square_rank(self.selected)
            if self.flipped:
                fs, rs = 7-fs, 7-rs
            col, row = fs*SQ, rs*SQ
            qp.fillRect(col, row, SQ, SQ, QColor(0, 255, 0, 100) if self.app.dark_theme_enabled else QColor(100, 200, 100, 120))

        if self.selected:
            for sq_idx in self.legal_moves_for_selected:
                f, r = chess.square_file(sq_idx), 7 - chess.square_rank(sq_idx)
                if self.flipped:
                    f, r = 7-f, 7-r
                col, row = f*SQ, r*SQ
                cx, cy = col + SQ//2, row + SQ//2
                target = self.app.current_board.piece_at(sq_idx)
                if target:
                    qp.setBrush(Qt.NoBrush)
                    pen = QPen(QColor(255, 50, 50, 200), 4)
                    qp.setPen(pen)
                    qp.drawEllipse(cx - SQ//2 + 4, cy - SQ//2 + 4, SQ-8, SQ-8)
                else:
                    qp.setBrush(QColor(200, 200, 200, 150) if self.app.dark_theme_enabled else QColor(0, 0, 0, 80))
                    qp.setPen(Qt.NoPen)
                    qp.drawEllipse(cx - 5, cy - 5, 10, 10)
                    
        # ДОБАВЯНЕ: Визуализиране на специални квадрати за промоция
        if self.selected:
            # Визуализиране на специални квадрати за промоция
            p = self.app.current_board.piece_at(self.selected)
            if p and p.piece_type == chess.PAWN:
                for sq_idx in self.legal_moves_for_selected:
                    target_rank = chess.square_rank(sq_idx)
                    is_promotion_square = False
                    if p.color == chess.WHITE and target_rank == 7:
                        is_promotion_square = True
                    elif p.color == chess.BLACK and target_rank == 0:
                        is_promotion_square = True
                    
                    if is_promotion_square:
                        f, r = chess.square_file(sq_idx), 7 - chess.square_rank(sq_idx)
                        if self.flipped:
                            f, r = 7-f, 7-r
                        col, row = f*SQ, r*SQ
                        
                        # Начертаване на специален индикатор за промоция
                        qp.setBrush(QColor(255, 215, 0, 150))  # Златен цвят за промоция
                        qp.setPen(QPen(QColor(255, 165, 0, 200), 3))
                        qp.drawRect(col + 5, row + 5, SQ - 10, SQ - 10)
                        
                        # Начертаване на корона в центъра
                        qp.setFont(QFont("Arial", 20, QFont.Bold))
                        qp.setPen(QColor(255, 215, 0))
                        qp.drawText(col + SQ//2 - 10, row + SQ//2 + 10, "♔" if p.color == chess.WHITE else "♚")

        if self.best_engine_move and self.show_engine_arrows:
            from_sq = self.best_engine_move.from_square
            to_sq = self.best_engine_move.to_square
            f1, r1 = chess.square_file(from_sq), 7 - chess.square_rank(from_sq)
            f2, r2 = chess.square_file(to_sq), 7 - chess.square_rank(to_sq)
            
            if self.flipped:
                f1, r1 = 7-f1, 7-r1
                f2, r2 = 7-f2, 7-r2
                
            x1, y1 = f1*SQ + SQ//2, r1*SQ + SQ//2
            x2, y2 = f2*SQ + SQ//2, r2*SQ + SQ//2
            
            col = QColor(0, 255, 0, 200)
            pen = QPen(col, SQ//6)
            pen.setCapStyle(Qt.RoundCap)
            qp.setPen(pen)
            qp.drawLine(x1, y1, x2, y2)
            
            qp.setBrush(col)
            qp.setPen(Qt.NoPen)
            head_size = SQ//3
            qp.drawEllipse(x2 - head_size//2, y2 - head_size//2, head_size, head_size)

        for sq in chess.SQUARES:
            piece = self.app.current_board.piece_at(sq)
            if piece:
                key = ("w" if piece.color else "b") + piece.symbol().lower()
                if key in self.pieces:
                    f = chess.square_file(sq)
                    r = 7 - chess.square_rank(sq)
                    
                    if self.flipped:
                        f, r = 7-f, 7-r
                    
                    dx = f*SQ + (SQ - self.pieces[key].width()) // 2
                    dy = r*SQ + (SQ - self.pieces[key].height()) // 2
                    qp.drawPixmap(dx, dy, self.pieces[key])
                else:
                    f = chess.square_file(sq)
                    r = 7 - chess.square_rank(sq)
                    
                    if self.flipped:
                        f, r = 7-f, 7-r
                    
                    qp.setPen(Qt.white if piece.color == chess.WHITE else Qt.black)
                    qp.setFont(QFont("Arial", 20, QFont.Bold))
                    qp.drawText(f*SQ, r*SQ, SQ, SQ, Qt.AlignCenter, piece.symbol())

    def mousePressEvent(self, e):
        """ВАЖНА КОРЕКЦИЯ: Поправена логика за избор и движение на фигури"""
        if self.app.is_engine_vs_engine:
            return

        x = e.x()
        y = e.y()
        
        # КОРЕКЦИЯ ТУК: Правилно изчисление при обърната дъска
        if self.flipped:
            f = 7 - (x // SQ)
            r = y // SQ
        else:
            f = x // SQ
            r = 7 - (y // SQ)
        
        sq = chess.square(f, r)

        # ВАЖНО: В режим човек срещу двигател, позволяваме взаимодействие само когато е ред на човека
        if not self.app.is_engine_vs_engine and self.app.game_board.turn != self.app.player_color:
            # Това е ред на двигателя, игнорираме кликовете
            return

        if self.selected is None:
            p = self.app.current_board.piece_at(sq)
            if p and p.color == self.app.player_color:
                self.selected = sq
                self.legal_moves_for_selected = [m.to_square for m in self.app.game_board.legal_moves if m.from_square == sq]
        else:
            move = chess.Move(self.selected, sq)
            
            p = self.app.current_board.piece_at(self.selected)
            if not p:
                self.selected = None
                self.legal_moves_for_selected = []
                self.update()
                return
            
            # Проверка за промоция
            is_prom = False
            if p.piece_type == chess.PAWN:
                target_rank = chess.square_rank(sq)
                if p.color == chess.WHITE and target_rank == 7:
                    is_prom = True
                elif p.color == chess.BLACK and target_rank == 0:
                    is_prom = True
            
            if is_prom:
                # ВАЖНА КОРЕКЦИЯ: Ходът без промоция не е легален, така че проверяваме дали има ЛЕГАЛНИ ходове с промоция
                legal_promotion_moves = [
                    m for m in self.app.game_board.legal_moves 
                    if m.from_square == self.selected and m.to_square == sq and m.promotion
                ]
                
                if legal_promotion_moves:
                    # Има легални ходове с промоция, отваряме диалога
                    self.promotion_dialog_open = True
                    self.promotion_target = (self.selected, sq)
                    self.open_promotion_dialog()
                else:
                    # Няма легални ходове за промоция, ресетваме селекцията
                    self.selected = None
                    self.legal_moves_for_selected = []
                return

            # Проверка дали ходът е легален
            if move in self.app.game_board.legal_moves:
                # Допълнителна проверка: фигурата трябва да е на играча
                if p.color == self.app.player_color:
                    self.selected = None
                    self.legal_moves_for_selected = []
                    self.human_move.emit(move)
            else:
                # Ако не е легален ход, проверяваме дали кликнали сме на друга наша фигура
                p2 = self.app.current_board.piece_at(sq)
                if p2 and p2.color == self.app.player_color:
                    self.selected = sq
                    self.legal_moves_for_selected = [m.to_square for m in self.app.game_board.legal_moves if m.from_square == sq]
                else:
                    self.selected = None
                    self.legal_moves_for_selected = []
        
        self.update()

    def open_promotion_dialog(self):
        """Отваря диалог за избор на фигура при промоция на пешка"""
        if not self.promotion_dialog_open or not self.promotion_target:
            return
        
        from_sq, to_sq = self.promotion_target
        
        # Проверяваме дали все още има фигура на началната позиция
        piece = self.app.current_board.piece_at(from_sq)
        if not piece:
            self.promotion_dialog_open = False
            self.promotion_target = None
            self.selected = None
            self.legal_moves_for_selected = []
            return
        
        # Проверяваме дали има легални ходове с промоция
        legal_promotion_moves = [
            m for m in self.app.game_board.legal_moves 
            if m.from_square == from_sq and m.to_square == to_sq and m.promotion
        ]
        
        if not legal_promotion_moves:
            QMessageBox.warning(self,
                              "Грешка" if self.app.language == "bg" else "Error",
                              "Няма легални ходове за промоция!" if self.app.language == "bg" else "No legal promotion moves!")
            self.promotion_dialog_open = False
            self.promotion_target = None
            self.selected = None
            self.legal_moves_for_selected = []
            return
        
        # Създаваме диалог за промоция
        dlg = PromotionDialog(piece.color, self.app.language, self)
        
        # Позиционираме диалога близо до дъската
        board_rect = self.geometry()
        dialog_pos = self.mapToGlobal(QPoint(board_rect.width() // 2 - 150, board_rect.height() // 2 - 50))
        dlg.move(dialog_pos)
        
        if dlg.exec_():
            move = chess.Move(from_sq, to_sq, promotion=dlg.result)
            
            # Проверяваме дали ходът е легален
            if move in self.app.game_board.legal_moves:
                self.human_move.emit(move)
            else:
                QMessageBox.warning(self,
                                  "Невалиден ход" if self.app.language == "bg" else "Invalid Move",
                                  "Ходът за промоция не е легален!" if self.app.language == "bg" else "This promotion move is not legal!")
        
        # Ресетваме всички променливи
        self.promotion_dialog_open = False
        self.promotion_target = None
        self.selected = None
        self.legal_moves_for_selected = []
        self.update()


class StyledClock(QLabel):
    def __init__(self, name, sec, base_color, text_color="white"):
        super().__init__()
        self.name = name
        self.time = float(sec)
        self.base_color = base_color
        self.text_color = text_color
        self.init_style()

    def init_style(self):
        self.setAlignment(Qt.AlignCenter)
        self.setFont(QFont("Consolas", 24, QFont.Bold))
        self.setFixedSize(140, 50)
        self.setStyleSheet(f"""
            background-color: {self.base_color};
            color: {self.text_color};
            border-radius: 10px;
            border: 2px solid #444;
        """)
        self.update_text()

    def update_text(self):
        total_seconds = int(self.time)
        m, s = divmod(total_seconds, 60)
        ms = int((self.time - total_seconds) * 10)
        if self.time < 60:
            self.setText(f"{m:01}:{s:02}.{ms:01}")
        else:
            self.setText(f"{m:02}:{s:02}")

    def tick(self, is_low=False):
        if self.time > 0:
            self.time -= 1.0
            self.update_text()
        if is_low:
            self.setStyleSheet(f"""
                background-color: #d9534f;
                color: white;
                border-radius: 10px;
                border: 2px solid red;
            """)

    def add_increment(self, inc):
        self.time += inc
        self.update_text()

    def reset(self, sec):
        self.time = float(sec)
        self.init_style()


class SimpleGameChartWidget(QWidget):
    def __init__(self, main_app=None, parent=None):
        super().__init__(parent)
        self.main_app = main_app
        self.eval_history = []
        self.move_history = []
        self.hover_index = -1
        self.setMinimumHeight(100)
        self.setMouseTracking(True)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
    def clear_chart(self):
        """Изчиства графиката"""
        self.eval_history = []
        self.move_history = []
        self.hover_index = -1
        self.update()
        
    def update_chart(self, move_count, move_notation, eval_cp):
        """Актуализира графиката с нов ход и оценка. move_count е броят полуходове."""
        # 1-ви полуход (бели) -> ход 1
        # 2-ри полуход (черни) -> ход 1
        # 3-ти полуход (бели) -> ход 2
        # 4-ти полуход (черни) -> ход 2
        display_number = (move_count + 1) // 2
        
        self.eval_history.append(eval_cp)
        self.move_history.append(f"{display_number}. {move_notation}")
        if len(self.eval_history) > 80: 
            self.eval_history = self.eval_history[-80:]
            self.move_history = self.move_history[-80:]
        self.update()
        
    def mouseMoveEvent(self, event):
        """Обработка на движение на мишката за tooltip"""
        if not self.eval_history:
            self.hover_index = -1
            self.update()
            return
            
        w = self.width()
        h = self.height()
        
        margin_left = 50
        margin_right = 20
        margin_top = 30
        margin_bottom = 25
        
        graph_width = w - margin_left - margin_right
        num_moves = len(self.eval_history)
        
        if num_moves <= 1:
            self.hover_index = -1
            self.update()
            return
            
        x = event.x()
        if x < margin_left or x > w - margin_right:
            self.hover_index = -1
            self.update()
            return
            
        rel_x = x - margin_left
        point_spacing = graph_width / (num_moves - 1)
        
        closest_index = int(round(rel_x / point_spacing))
        closest_index = max(0, min(closest_index, num_moves - 1))
        
        point_x = margin_left + closest_index * point_spacing
        if abs(x - point_x) < 15:
            self.hover_index = closest_index
            
            eval_cp = self.eval_history[closest_index]
            eval_value = eval_cp/100
            
            move_text = self.move_history[closest_index]
            move_parts = move_text.split('. ')
            if len(move_parts) > 1:
                move_num = move_parts[0]
                move_notation = move_parts[1]
            else:
                move_num = "?"
                move_notation = move_text
            
            if eval_value > 1.0:
                eval_color = "green"
                eval_desc = "Предимство за белите" if self.main_app and self.main_app.language == "bg" else "White advantage"
            elif eval_value < -1.0:
                eval_color = "red"
                eval_desc = "Предимство за черните" if self.main_app and self.main_app.language == "bg" else "Black advantage"
            elif eval_value > 0.3:
                eval_color = "lightgreen"
                eval_desc = "Леко предимство за белите" if self.main_app and self.main_app.language == "bg" else "Slight white advantage"
            elif eval_value < -0.3:
                eval_color = "orange"
                eval_desc = "Леко предимство за черните" if self.main_app and self.main_app.language == "bg" else "Slight black advantage"
            else:
                eval_color = "orange"
                eval_desc = "Равна позиция" if self.main_app and self.main_app.language == "bg" else "Equal position"
            
            if abs(eval_value) > 10:
                eval_text = f"Мат след {int(abs(eval_value))} хода"
                if eval_value > 0:
                    eval_desc = "Белите дават мат" if self.main_app and self.main_app.language == "bg" else "White mates"
                else:
                    eval_desc = "Черните дават мат" if self.main_app and self.main_app.language == "bg" else "Black mates"
            else:
                eval_text = f"{eval_value:+.2f}"
            
            tooltip_text = f"<b>{move_text}</b><br>" \
                         f"<span style='color: {eval_color}'><b>Оценка: {eval_text}</b></span><br>" \
                         f"{eval_desc}<br>"
            
            QToolTip.showText(event.globalPos(), tooltip_text, self)
        else:
            self.hover_index = -1
            QToolTip.hideText()
            
        self.update()
        
    def leaveEvent(self, event):
        """При напускане на widget-a скриваме tooltip"""
        self.hover_index = -1
        QToolTip.hideText()
        self.update()
        
    def paintEvent(self, e):
        qp = QPainter(self)
        qp.setRenderHint(QPainter.Antialiasing)
        
        w = self.width()
        h = self.height()
        
        if h < 50:
            return
        
        dark_theme = False
        if self.main_app:
            dark_theme = self.main_app.dark_theme_enabled
        elif self.parent() and hasattr(self.parent().parent(), 'dark_theme_enabled'):
            dark_theme = self.parent().parent().dark_theme_enabled
        
        if dark_theme:
            background_color = QColor(20, 20, 30)
            grid_color = QColor(80, 80, 100, 100)
            text_color = QColor(240, 240, 255)
            axis_color = QColor(180, 180, 220)
            
            eval_colors = {
                'very_positive': QColor(100, 255, 100),
                'positive': QColor(150, 220, 100),
                'slight_positive': QColor(200, 255, 150),
                'neutral': QColor(255, 165, 0),
                'slight_negative': QColor(255, 200, 100),
                'negative': QColor(255, 150, 100),
                'very_negative': QColor(255, 100, 100),
                'mate': QColor(255, 50, 50)
            }
            
            line_color = QColor(100, 180, 255, 200)
            hover_color = QColor(255, 200, 50, 230)
            gradient_start = QColor(30, 30, 50, 150)
            gradient_end = QColor(30, 30, 50, 50)
        else:
            background_color = QColor(245, 245, 255)
            grid_color = QColor(180, 180, 220, 100)
            text_color = QColor(30, 30, 60)
            axis_color = QColor(100, 100, 160)
            
            eval_colors = {
                'very_positive': QColor(0, 200, 0),
                'positive': QColor(100, 180, 0),
                'slight_positive': QColor(150, 220, 50),
                'neutral': QColor(255, 140, 0),
                'slight_negative': QColor(255, 180, 50),
                'negative': QColor(255, 120, 50),
                'very_negative': QColor(255, 80, 80),
                'mate': QColor(220, 50, 50)
            }
            
            line_color = QColor(70, 130, 220, 200)
            hover_color = QColor(255, 200, 50, 230)
            gradient_start = QColor(200, 220, 255, 150)
            gradient_end = QColor(200, 220, 255, 50)
        
        gradient = QLinearGradient(0, 0, 0, h)
        gradient.setColorAt(0, gradient_start)
        gradient.setColorAt(1, gradient_end)
        qp.fillRect(0, 0, w, h, background_color)
        qp.fillRect(0, 0, w, h, gradient)
        
        if not self.eval_history:
            qp.setPen(text_color)
            qp.setFont(QFont("Arial", 12, QFont.Bold))
            text = "Няма данни за оценка" if self.main_app and self.main_app.language == "bg" else "No evaluation data"
            text_width = qp.fontMetrics().width(text)
            qp.drawText(w//2 - text_width//2, h//2, text)
            return
        
        margin_left = max(40, w * 0.05)
        margin_right = max(20, w * 0.03)
        margin_top = max(30, h * 0.1)
        margin_bottom = max(25, h * 0.1)
        
        graph_width = w - margin_left - margin_right
        graph_height = h - margin_top - margin_bottom
        
        if graph_width < 50 or graph_height < 50:
            return
        
        max_eval = max(max(self.eval_history), 300) if self.eval_history else 300
        min_eval = min(min(self.eval_history), -300) if self.eval_history else -300
        
        eval_range = max_eval - min_eval
        if eval_range < 100:
            eval_range = 200
            max_eval = 100
            min_eval = -100
        else:
            padding = eval_range * 0.15
            max_eval += padding
            min_eval -= padding
        
        qp.setPen(QPen(grid_color, 1, Qt.DotLine))
        num_horizontal_lines = min(8, int(graph_height / 20))
        for i in range(num_horizontal_lines + 1):
            y = margin_top + i * (graph_height / num_horizontal_lines)
            qp.drawLine(int(margin_left), int(y), int(w - margin_right), int(y))
        
        num_moves = len(self.eval_history)
        if num_moves > 1:
            qp.setPen(QPen(grid_color, 1, Qt.DashLine))
            for i in range(num_moves):
                x = margin_left + i * (graph_width / (num_moves - 1))
                qp.drawLine(int(x), int(margin_top), int(x), int(h - margin_bottom))
        
        # Линия на X оста
        qp.setPen(QPen(axis_color, 2))
        qp.drawLine(int(margin_left), int(h - margin_bottom), int(w - margin_right), int(h - margin_bottom))
        
        # Разграфяване по X (ходове)
        qp.setPen(text_color)
        qp.setFont(QFont("Arial", 8))
        if num_moves > 1:
            # Показваме етикети за ходовете
            step = max(1, num_moves // 10)
            for i in range(0, num_moves, step):
                x = margin_left + i * (graph_width / (num_moves - 1))
                move_text = self.move_history[i]
                # Извличаме само номера на хода (преди точката)
                try:
                    display_num = move_text.split('.')[0]
                except:
                    display_num = str(i + 1)
                
                # Рисуваме малка чертичка (tick)
                qp.drawLine(int(x), int(h - margin_bottom), int(x), int(h - margin_bottom + 5))
                # Рисуваме номера на хода
                qp.drawText(int(x - 10), int(h - margin_bottom + 20), display_num)

        # Линия на Y оста
        qp.setPen(QPen(axis_color, 2))
        qp.drawLine(int(margin_left), int(margin_top), int(margin_left), int(h - margin_bottom))
        
        # Разграфяване по Y (оценка)
        qp.setPen(text_color)
        num_y_labels = 5
        for i in range(num_y_labels + 1):
            y = margin_top + i * (graph_height / num_y_labels)
            eval_val = max_eval - i * (max_eval - min_eval) / num_y_labels
            
            if abs(eval_val) > 1000:
                label = "Мат" if self.main_app and self.main_app.language == "bg" else "Mate"
            else:
                label = f"{eval_val/100:+.1f}"
            
            # Рисуваме малка чертичка (tick)
            qp.drawLine(int(margin_left - 5), int(y), int(margin_left), int(y))
            # Рисуваме етикета на оценката
            text_width = qp.fontMetrics().width(label)
            qp.drawText(int(margin_left - text_width - 10), int(y + 5), label)
        
        zero_y = margin_top + graph_height * (1 - (-min_eval) / (max_eval - min_eval))
        qp.setPen(QPen(axis_color, 3, Qt.DashLine))
        qp.drawLine(int(margin_left), int(zero_y), int(w - margin_right), int(zero_y))
        
        points = []
        for i, eval_cp in enumerate(self.eval_history):
            x = margin_left + i * (graph_width / max(num_moves - 1, 1))
            y = margin_top + graph_height * (1 - (eval_cp - min_eval) / (max_eval - min_eval))
            points.append((x, y))
        
        if len(points) > 1:
            fill_path = QPainterPath()
            fill_path.moveTo(points[0][0], points[0][1])
            
            for i in range(1, len(points)):
                x, y = points[i]
                fill_path.lineTo(x, y)
            
            fill_path.lineTo(points[-1][0], h - margin_bottom)
            fill_path.lineTo(points[0][0], h - margin_bottom)
            fill_path.closeSubpath()
            
            fill_gradient = QLinearGradient(0, margin_top, 0, h - margin_bottom)
            fill_gradient.setColorAt(0, QColor(100, 180, 255, 80))
            fill_gradient.setColorAt(1, QColor(100, 180, 255, 20))
            qp.fillPath(fill_path, fill_gradient)
        
        if len(points) > 1:
            pen = QPen(line_color, max(2, int(w * 0.003)))
            pen.setCapStyle(Qt.RoundCap)
            pen.setJoinStyle(Qt.RoundJoin)
            qp.setPen(pen)
            
            if len(points) >= 3:
                path = QPainterPath()
                path.moveTo(points[0][0], points[0][1])
                
                for i in range(1, len(points)):
                    x0, y0 = points[i-1]
                    x1, y1 = points[i]
                    
                    if i < len(points) - 1:
                        x2, y2 = points[i+1]
                        cp1_x = x0 + (x1 - x0) * 0.3
                        cp1_y = y0
                        cp2_x = x1 - (x2 - x1) * 0.3
                        cp2_y = y1
                        path.cubicTo(cp1_x, cp1_y, cp2_x, cp2_y, x1, y1)
                    else:
                        path.lineTo(x1, y1)
                
                qp.drawPath(path)
            else:
                for i in range(len(points)-1):
                    x1, y1 = points[i]
                    x2, y2 = points[i+1]
                    qp.drawLine(int(x1), int(y1), int(x2), int(y2))
        
        for i, (x, y) in enumerate(points):
            eval_cp = self.eval_history[i]
            
            base_point_size = max(4, int(w * 0.008))
            
            if eval_cp > 300:
                color = eval_colors['very_positive']
                point_size = base_point_size + 4
            elif eval_cp > 100:
                color = eval_colors['positive']
                point_size = base_point_size + 2
            elif eval_cp > 30:
                color = eval_colors['slight_positive']
                point_size = base_point_size + 1
            elif eval_cp < -300:
                color = eval_colors['very_negative']
                point_size = base_point_size + 4
            elif eval_cp < -100:
                color = eval_colors['negative']
                point_size = base_point_size + 2
            elif eval_cp < -30:
                color = eval_colors['slight_negative']
                point_size = base_point_size + 1
            else:
                color = eval_colors['neutral']
                point_size = base_point_size + 2
            
            if abs(eval_cp) > 1000:
                color = eval_colors['mate']
                point_size = base_point_size + 6
            
            if i == self.hover_index:
                color = hover_color
                point_size = base_point_size + 8
            
            qp.setBrush(color)
            
            shadow_pen = QPen(QColor(0, 0, 0, 100), 1)
            qp.setPen(shadow_pen)
            qp.drawEllipse(int(x) - point_size//2 + 1, int(y) - point_size//2 + 1, point_size, point_size)
            
            if i == self.hover_index:
                qp.setPen(QPen(QColor(0, 0, 0), 2))
            else:
                qp.setPen(QPen(QColor(255, 255, 255, 200), 1))
            
            qp.drawEllipse(int(x) - point_size//2, int(y) - point_size//2, point_size, point_size)
            
            if i != self.hover_index:
                inner_color = QColor(255, 255, 255, 180)
                qp.setBrush(inner_color)
                inner_size = point_size - 4
                if inner_size > 0:
                    qp.drawEllipse(int(x) - inner_size//2, int(y) - inner_size//2, inner_size, inner_size)
        
        qp.setPen(text_color)
        qp.setFont(QFont("Arial", max(10, int(h * 0.02)), QFont.Bold))
        
        x_label = "ХОД №" if self.main_app and self.main_app.language == "bg" else "MOVE #"
        text_width = qp.fontMetrics().width(x_label)
        qp.drawText(w//2 - text_width//2, h - 10, x_label)
        
        if h > 100:
            title = "ГРАФИКА НА ОЦЕНКАТА" if self.main_app and self.main_app.language == "bg" else "EVALUATION CHART"
            qp.setFont(QFont("Arial", max(12, int(h * 0.025)), QFont.Bold))
            title_width = qp.fontMetrics().width(title)
            qp.drawText(w//2 - title_width//2, 20, title)


class HighlightsWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.main_app = parent
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        
        self.highlights_text = QTextEdit()
        self.highlights_text.setReadOnly(True)
        self.highlights_text.setFont(QFont("Consolas", 9))
        self.highlights_text.setMaximumHeight(200)
        layout.addWidget(self.highlights_text)
        
    def update_highlights(self, board):
        if not board:
            return
            
        text = ""
        
        white_threatened = []
        black_threatened = []
        
        for square in chess.SQUARES:
            piece = board.piece_at(square)
            if piece:
                attackers = board.attackers(not piece.color, square)
                if attackers:
                    piece_name = self.get_piece_name(piece)
                    if piece.color == chess.WHITE:
                        white_threatened.append(f"{piece_name} на {chess.square_name(square)}" if self.main_app.language == "bg" else f"{piece_name} on {chess.square_name(square)}")
                    else:
                        black_threatened.append(f"{piece_name} на {chess.square_name(square)}" if self.main_app.language == "bg" else f"{piece_name} on {chess.square_name(square)}")
        
        center_squares = [chess.E4, chess.D4, chess.E5, chess.D5]
        white_center_control = 0
        black_center_control = 0
        
        for square in center_squares:
            if board.is_attacked_by(chess.WHITE, square):
                white_center_control += 1
            if board.is_attacked_by(chess.BLACK, square):
                black_center_control += 1
        
        white_pieces = sum([len(board.pieces(pt, chess.WHITE)) for pt in range(1, 7)])
        black_pieces = sum([len(board.pieces(pt, chess.BLACK)) for pt in range(1, 7)])
        
        temp_board = board.copy()
        temp_board.turn = chess.WHITE
        white_legal_moves = temp_board.legal_moves.count()
        temp_board.turn = chess.BLACK
        black_legal_moves = temp_board.legal_moves.count()
        
        text += "══════════════════════════════\n"
        text += "СТАТИСТИКА НА ПОЗИЦИЯТА:\n" if self.main_app.language == "bg" else "POSITION STATISTICS:\n"
        text += "══════════════════════════════\n\n"
        
        text += f"БЕЛИ:\n" if self.main_app.language == "bg" else f"WHITE:\n"
        text += f"  • Фигури: {white_pieces}\n" if self.main_app.language == "bg" else f"  • Pieces: {white_pieces}\n"
        text += f"  • Легални ходове: {white_legal_moves}\n" if self.main_app.language == "bg" else f"  • Legal moves: {white_legal_moves}\n"
        text += f"  • Контрол на центъра: {white_center_control}/4\n" if self.main_app.language == "bg" else f"  • Center control: {white_center_control}/4\n"
        if white_threatened:
            text += f"  • Заплашени фигури: {', '.join(white_threatened)}\n" if self.main_app.language == "bg" else f"  • Threatened pieces: {', '.join(white_threatened)}\n"
        else:
            text += f"  • Заплашени фигури: Няма\n" if self.main_app.language == "bg" else f"  • Threatened pieces: None\n"
        
        text += f"\nЧЕРНИ:\n" if self.main_app.language == "bg" else f"\nBLACK:\n"
        text += f"  • Фигури: {black_pieces}\n" if self.main_app.language == "bg" else f"  • Pieces: {black_pieces}\n"
        text += f"  • Легални ходове: {black_legal_moves}\n" if self.main_app.language == "bg" else f"  • Legal moves: {black_legal_moves}\n"
        text += f"  • Контрол на центъра: {black_center_control}/4\n" if self.main_app.language == "bg" else f"  • Center control: {black_center_control}/4\n"
        if black_threatened:
            text += f"  • Заплашени фигури: {', '.join(black_threatened)}\n" if self.main_app.language == "bg" else f"  • Threatened pieces: {', '.join(black_threatened)}\n"
        else:
            text += f"  • Заплашени фигури: Няма\n" if self.main_app.language == "bg" else f"  • Threatened pieces: None\n"
        
        if board.is_check():
            text += f"\n══════════════════════════════\n"
            text += f"ШАХ! На ход е {'БЕЛИ' if board.turn == chess.WHITE else 'ЧЕРНИ'}\n" if self.main_app.language == "bg" else f"CHECK! {'WHITE' if board.turn == chess.WHITE else 'BLACK'} to move\n"
        
        self.highlights_text.setText(text)
    
    def get_piece_name(self, piece):
        if self.main_app.language == "bg":
            names = {
                chess.PAWN: "Пешка",
                chess.KNIGHT: "Кон",
                chess.BISHOP: "Офицер",
                chess.ROOK: "Топ",
                chess.QUEEN: "Царица",
                chess.KING: "Цар"
            }
            color = "Бял" if piece.color == chess.WHITE else "Черен"
        else:
            names = {
                chess.PAWN: "Pawn",
                chess.KNIGHT: "Knight",
                chess.BISHOP: "Bishop",
                chess.ROOK: "Rook",
                chess.QUEEN: "Queen",
                chess.KING: "King"
            }
            color = "White" if piece.color == chess.WHITE else "Black"
        return f"{color} {names.get(piece.piece_type, 'Фигура' if self.main_app.language == 'bg' else 'Piece')}"


class Settings:
    def __init__(self):
        self.settings_file = "pychess_settings.json"
        self.default_settings = {
            "dark_theme": True,
            "engine1_path": "",
            "engine2_path": "",
            "engine1_threads": 1,
            "engine2_threads": 1,
            "book_path": "",
            "book_max_depth": 10,
            "pieces_folder": "",
            "time_control": 300,
            "increment": 0,
            "player_color": "white",
            "game_mode": "human_vs_engine",
            "engine_strength": "time_based",
            "light_square_color": "#f0d9b5",
            "dark_square_color": "#b58863",
            "pv_moves_display": 12,
            "theme": "dark_blue",
            "language": "bg",
            "show_engine_arrows": True
        }
        self.current = {}
        self.load()
        
    def load(self):
        try:
            if os.path.exists(self.settings_file):
                with open(self.settings_file, 'r') as f:
                    self.current = json.load(f)
                for key in list(self.current.keys()):
                    if key not in self.default_settings:
                        del self.current[key]
            else:
                self.current = self.default_settings.copy()
        except:
            self.current = self.default_settings.copy()
            
    def save(self):
        try:
            with open(self.settings_file, 'w') as f:
                json.dump(self.current, f, indent=4)
        except:
            pass
            
    def get(self, key, default=None):
        return self.current.get(key, self.default_settings.get(key, default))
        
    def set(self, key, value):
        self.current[key] = value
        self.save()


class BookDisplayDialog(QDialog):
    def __init__(self, parent, entries, total_weight):
        super().__init__(parent)
        self.setWindowTitle("Отваряния - детайли" if parent.language == "bg" else "Book Moves - Details")
        self.resize(500, 400)
        self.entries = entries
        self.total_weight = total_weight
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels([
            "Ход" if self.parent().language == "bg" else "Move",
            "Процент" if self.parent().language == "bg" else "Percentage",
            "Тежест" if self.parent().language == "bg" else "Weight"
        ])
        
        self.table.setRowCount(len(self.entries))
        
        for i, entry in enumerate(self.entries):
            move_item = QTableWidgetItem(str(entry.move))
            self.table.setItem(i, 0, move_item)
            
            percent = (entry.weight / self.total_weight) * 100
            percent_item = QTableWidgetItem(f"{percent:.2f}%")
            percent_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(i, 1, percent_item)
            
            weight_item = QTableWidgetItem(str(entry.weight))
            weight_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(i, 2, weight_item)
        
        self.table.resizeColumnsToContents()
        layout.addWidget(self.table)
        
        btn_close = QPushButton("Затвори" if self.parent().language == "bg" else "Close")
        btn_close.clicked.connect(self.accept)
        layout.addWidget(btn_close)


class ColorPaletteDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Палитра за цветове на дъската" if parent.language == "bg" else "Board Color Palette")
        self.setFixedSize(500, 400)
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        color_group = QGroupBox("Цветове на дъската" if self.parent().language == "bg" else "Board Colors")
        color_layout = QGridLayout()
        
        light_label = QLabel("Светли квадрати:" if self.parent().language == "bg" else "Light Squares:")
        color_layout.addWidget(light_label, 0, 0)
        
        self.light_color_btn = QPushButton()
        self.light_color_btn.setFixedSize(60, 30)
        self.light_color_btn.clicked.connect(self.choose_light_color)
        color_layout.addWidget(self.light_color_btn, 0, 1)
        
        self.light_color_edit = QLineEdit()
        self.light_color_edit.setText(self.parent().light_square_color.name())
        self.light_color_edit.textChanged.connect(self.light_color_changed)
        color_layout.addWidget(self.light_color_edit, 0, 2)
        
        dark_label = QLabel("Тъмни квадрати:" if self.parent().language == "bg" else "Dark Squares:")
        color_layout.addWidget(dark_label, 1, 0)
        
        self.dark_color_btn = QPushButton()
        self.dark_color_btn.setFixedSize(60, 30)
        self.dark_color_btn.clicked.connect(self.choose_dark_color)
        color_layout.addWidget(self.dark_color_btn, 1, 1)
        
        self.dark_color_edit = QLineEdit()
        self.dark_color_edit.setText(self.parent().dark_square_color.name())
        self.dark_color_edit.textChanged.connect(self.dark_color_changed)
        color_layout.addWidget(self.dark_color_edit, 1, 2)
        
        color_group.setLayout(color_layout)
        layout.addWidget(color_group)
        
        preset_group = QGroupBox("Предварителни цветови схеми" if self.parent().language == "bg" else "Preset Color Schemes")
        preset_layout = QGridLayout()
        
        presets = [
            ("Класическа", "#f0d9b5", "#b58863"),
            ("Зелена", "#eeeed2", "#769656"),
            ("Синя", "#dee3e6", "#8ca2ad"),
            ("Черно-бела", "#ffffff", "#888888"),
            ("Кафява", "#d18b47", "#ffce9e"),
            ("Лилава", "#9d7cbf", "#d1b2e3"),
            ("Червена", "#ffcccc", "#cc6666"),
            ("Тъмна", "#666666", "#333333"),
            ("Морска", "#b3d9ff", "#6699cc")
        ]
        
        row, col = 0, 0
        for name, light, dark in presets:
            btn = QPushButton(name)
            btn.setFixedSize(120, 40)
            btn.clicked.connect(lambda checked, l=light, d=dark: self.apply_preset(l, d))
            preset_layout.addWidget(btn, row, col)
            col += 1
            if col > 2:
                col = 0
                row += 1
        
        preset_group.setLayout(preset_layout)
        layout.addWidget(preset_group)
        
        btn_layout = QHBoxLayout()
        self.apply_btn = QPushButton("Приложи" if self.parent().language == "bg" else "Apply")
        self.apply_btn.clicked.connect(self.apply_colors)
        self.cancel_btn = QPushButton("Отказ" if self.parent().language == "bg" else "Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        self.default_btn = QPushButton("По подразбиране" if self.parent().language == "bg" else "Default")
        self.default_btn.clicked.connect(self.apply_default)
        
        btn_layout.addWidget(self.apply_btn)
        btn_layout.addWidget(self.default_btn)
        btn_layout.addWidget(self.cancel_btn)
        layout.addLayout(btn_layout)
        
        self.update_button_colors()
    
    def update_button_colors(self):
        light_color = self.parent().light_square_color
        dark_color = self.parent().dark_square_color
        
        self.light_color_btn.setStyleSheet(f"background-color: {light_color.name()}; border: 2px solid #555;")
        self.dark_color_btn.setStyleSheet(f"background-color: {dark_color.name()}; border: 2px solid #555;")
    
    def light_color_changed(self, text):
        try:
            color = QColor(text)
            if color.isValid():
                self.parent().light_square_color = color
                self.update_button_colors()
        except:
            pass
    
    def dark_color_changed(self, text):
        try:
            color = QColor(text)
            if color.isValid():
                self.parent().dark_square_color = color
                self.update_button_colors()
        except:
            pass
    
    def choose_light_color(self):
        color = QColorDialog.getColor(self.parent().light_square_color, self)
        
        if color.isValid():
            self.parent().light_square_color = color
            self.light_color_edit.setText(color.name())
            self.update_button_colors()
    
    def choose_dark_color(self):
        color = QColorDialog.getColor(self.parent().dark_square_color, self)
        if color.isValid():
            self.parent().dark_square_color = color
            self.dark_color_edit.setText(color.name())
            self.update_button_colors()
    
    def apply_preset(self, light_hex, dark_hex):
        self.parent().light_square_color = QColor(light_hex)
        self.parent().dark_square_color = QColor(dark_hex)
        self.light_color_edit.setText(light_hex)
        self.dark_color_edit.setText(dark_hex)
        self.update_button_colors()
    
    def apply_default(self):
        self.apply_preset("#f0d9b5", "#b58863")
    
    def apply_colors(self):
        self.parent().board_w.update()
        self.accept()

class PGNGameDialog(QDialog):
    """Диалогов прозорец за избор на партия от PGN база"""
    
    load_game = pyqtSignal(int)  # Сигнал за зареждане на игра
    
    def __init__(self, parent=None, pgn_games=None):
        super().__init__(parent)
        self.main_app = parent
        self.pgn_games = pgn_games or []
        self.selected_game_index = -1
        self.setWindowTitle("Избор на партия от PGN" if parent.language == "bg" else "Select Game from PGN")
        self.resize(900, 600)
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        self.setWindowFlags(Qt.Dialog | Qt.WindowMinimizeButtonHint | Qt.WindowCloseButtonHint)
        
        # Заглавие
        title_label = QLabel("PGN База Данни - Избор на Партия" if self.main_app.language == "bg" else "PGN Database - Select Game")
        title_label.setFont(QFont("Arial", 14, QFont.Bold))
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)
        
        # Таблица с партиите
        self.games_table = QTableWidget()
        self.games_table.setColumnCount(8)
        headers = ["№", "Събитие" if self.main_app.language == "bg" else "Event", 
                  "Бели" if self.main_app.language == "bg" else "White",
                  "Черни" if self.main_app.language == "bg" else "Black",
                  "Резултат" if self.main_app.language == "bg" else "Result",
                  "Дата" if self.main_app.language == "bg" else "Date",
                  "Ходове" if self.main_app.language == "bg" else "Moves",
                  "Отваряне" if self.main_app.language == "bg" else "Opening"]
        self.games_table.setHorizontalHeaderLabels(headers)
        self.games_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.games_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.games_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.games_table.doubleClicked.connect(self.load_selected_game)
        self.games_table.clicked.connect(self.update_preview)
        
        # Настройване на таблицата
        self.games_table.horizontalHeader().setStretchLastSection(True)
        self.games_table.verticalHeader().setVisible(False)
        self.games_table.setAlternatingRowColors(True)
        
        layout.addWidget(self.games_table)
        
        # Разделител
        splitter = QSplitter(Qt.Horizontal)
        
        # Детайли за избраната партия
        details_group = QGroupBox("Детайли на партията" if self.main_app.language == "bg" else "Game Details")
        details_layout = QVBoxLayout()
        
        self.details_text = QTextEdit()
        self.details_text.setReadOnly(True)
        self.details_text.setFont(QFont("Consolas", 10))
        details_layout.addWidget(self.details_text)
        
        details_group.setLayout(details_layout)
        splitter.addWidget(details_group)
        
        # Преглед на първите няколко хода
        preview_group = QGroupBox("Преглед на ходовете" if self.main_app.language == "bg" else "Moves Preview")
        preview_layout = QVBoxLayout()
        
        self.preview_text = QTextEdit()
        self.preview_text.setReadOnly(True)
        self.preview_text.setFont(QFont("Consolas", 10))
        preview_layout.addWidget(self.preview_text)
        
        preview_group.setLayout(preview_layout)
        splitter.addWidget(preview_group)
        
        splitter.setSizes([400, 300])
        layout.addWidget(splitter)
        
        # Бутони
        button_layout = QHBoxLayout()
        
        self.load_button = QPushButton("Зареди избраната партия" if self.main_app.language == "bg" else "Load Selected Game")
        self.load_button.clicked.connect(self.load_selected_game)
        self.load_button.setEnabled(False)
        
        self.close_button = QPushButton("Затвори" if self.main_app.language == "bg" else "Close")
        self.close_button.clicked.connect(self.reject)
        
        self.next_button = QPushButton("Следваща партия" if self.main_app.language == "bg" else "Next Game")
        self.next_button.clicked.connect(self.next_game)
        
        self.prev_button = QPushButton("Предишна партия" if self.main_app.language == "bg" else "Previous Game")
        self.prev_button.clicked.connect(self.prev_game)
        
        button_layout.addWidget(self.prev_button)
        button_layout.addWidget(self.next_button)
        button_layout.addStretch()
        button_layout.addWidget(self.load_button)
        button_layout.addWidget(self.close_button)
        
        layout.addLayout(button_layout)
        
        # Зареждане на данните
        self.load_games()
        
    def load_games(self):
        """Зарежда всички партии в таблицата"""
        self.games_table.setRowCount(len(self.pgn_games))
        
        for i, game in enumerate(self.pgn_games):
            # Номер
            num_item = QTableWidgetItem(str(i + 1))
            num_item.setTextAlignment(Qt.AlignCenter)
            self.games_table.setItem(i, 0, num_item)
            
            # Събитие
            event = game.headers.get("Event", "N/A")
            self.games_table.setItem(i, 1, QTableWidgetItem(event))
            
            # Бели
            white = game.headers.get("White", "N/A")
            self.games_table.setItem(i, 2, QTableWidgetItem(white))
            
            # Черни
            black = game.headers.get("Black", "N/A")
            self.games_table.setItem(i, 3, QTableWidgetItem(black))
            
            # Резултат
            result = game.headers.get("Result", "*")
            self.games_table.setItem(i, 4, QTableWidgetItem(result))
            
            # Дата
            date = game.headers.get("Date", "????.??.??")
            self.games_table.setItem(i, 5, QTableWidgetItem(date))
            
            # Брой ходове
            moves_count = len(list(game.mainline_moves()))
            moves_item = QTableWidgetItem(str(moves_count))
            moves_item.setTextAlignment(Qt.AlignCenter)
            self.games_table.setItem(i, 6, moves_item)
            
            # Отваряне
            opening = game.headers.get("Opening", "")
            eco = game.headers.get("ECO", "")
            if opening and eco:
                opening_text = f"{eco} {opening}"
            elif opening:
                opening_text = opening
            elif eco:
                opening_text = eco
            else:
                opening_text = ""
            self.games_table.setItem(i, 7, QTableWidgetItem(opening_text))
        
        # Автоматично настройване на ширината на колоните
        self.games_table.resizeColumnsToContents()
        
        # Избираме първата партия по подразбиране
        if self.pgn_games:
            self.games_table.selectRow(0)
            self.update_preview()
    
    def update_preview(self):
        """Обновява прегледа за текущо избраната партия"""
        selected_rows = self.games_table.selectedItems()
        if not selected_rows:
            return
            
        row = selected_rows[0].row()
        if row < 0 or row >= len(self.pgn_games):
            return
            
        game = self.pgn_games[row]
        self.selected_game_index = row
        
        # Обновяваме детайлите
        details = self.get_game_details(game)
        self.details_text.setText(details)
        
        # Обновяваме прегледа на ходовете
        preview = self.get_moves_preview(game)
        self.preview_text.setText(preview)
        
        # Активираме бутона за зареждане
        self.load_button.setEnabled(True)
    
    def get_game_details(self, game):
        """Връща детайли за партията като текст"""
        details = ""
        
        if self.main_app.language == "bg":
            details += "══════════════════════════════\n"
            details += "   ДЕТАЙЛИ ЗА ПАРТИЯТА\n"
            details += "══════════════════════════════\n\n"
            
            headers = [
                ("Събитие", "Event"),
                ("Бели", "White"),
                ("Черни", "Black"),
                ("Резултат", "Result"),
                ("Дата", "Date"),
                ("Място", "Site"),
                ("Кръг", "Round"),
                ("Отваряне", "Opening"),
                ("ECO", "ECO"),
                ("Вариант", "Variation"),
                ("Защита", "Defense")
            ]
        else:
            details += "══════════════════════════════\n"
            details += "      GAME DETAILS\n"
            details += "══════════════════════════════\n\n"
            
            headers = [
                ("Event", "Event"),
                ("White", "White"),
                ("Black", "Black"),
                ("Result", "Result"),
                ("Date", "Date"),
                ("Site", "Site"),
                ("Round", "Round"),
                ("Opening", "Opening"),
                ("ECO", "ECO"),
                ("Variation", "Variation"),
                ("Defense", "Defense")
            ]
        
        for display_name, header_name in headers:
            value = game.headers.get(header_name, "")
            if value:
                details += f"{display_name}: {value}\n"
        
        # Брой ходове
        moves_count = len(list(game.mainline_moves()))
        if self.main_app.language == "bg":
            details += f"\nБрой ходове: {moves_count}\n"
        else:
            details += f"\nNumber of moves: {moves_count}\n"
        
        return details
    
    def get_moves_preview(self, game, max_moves=20):
        """Връща преглед на първите няколко хода от партията"""
        if self.main_app.language == "bg":
            preview = "Първи ходове:\n"
            preview += "══════════════════════════════\n\n"
        else:
            preview = "First moves:\n"
            preview += "══════════════════════════════\n\n"
        
        # Вземаме главната вариация
        board = game.board()
        moves = list(game.mainline_moves())
        
        move_text = ""
        move_number = 1
        
        for i, move in enumerate(moves[:max_moves]):
            san = board.san(move)
            
            if i % 2 == 0:  # Ход на белите
                move_text += f"{move_number}. {san} "
            else:  # Ход на черните
                move_text += f"{san}\n"
                move_number += 1
            
            board.push(move)
        
        # Ако има нечетен брой ходове, добавяме нов ред
        if len(moves[:max_moves]) % 2 == 1:
            move_text += "\n"
        
        preview += move_text
        
        if len(moves) > max_moves:
            if self.main_app.language == "bg":
                preview += f"\n... и още {len(moves) - max_moves} хода"
            else:
                preview += f"\n... and {len(moves) - max_moves} more moves"
        
        return preview
    
    def load_selected_game(self):
        """Зарежда избраната игра без да затваря диалога"""
        if self.selected_game_index >= 0:
            self.load_game.emit(self.selected_game_index)
    
    def next_game(self):
        """Избира следващата партия"""
        if self.pgn_games and self.selected_game_index < len(self.pgn_games) - 1:
            self.selected_game_index += 1
            self.games_table.selectRow(self.selected_game_index)
            self.update_preview()
    
    def prev_game(self):
        """Избира предишната партия"""
        if self.pgn_games and self.selected_game_index > 0:
            self.selected_game_index -= 1
            self.games_table.selectRow(self.selected_game_index)
            self.update_preview()


class ProgressDialog(QDialog):
    """Диалог за прогрес при зареждане на PGN"""
    
    def __init__(self, parent=None, title="Зареждане..."):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setFixedSize(400, 150)
        self.setModal(True)
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        self.label = QLabel("Зареждане на PGN файл...")
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setFont(QFont("Arial", 10, QFont.Bold))
        layout.addWidget(self.label)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)
        
        self.details_label = QLabel("")
        self.details_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.details_label)
        
    def set_progress(self, value, text=None):
        self.progress_bar.setValue(value)
        if text:
            self.label.setText(text)
            
    def set_details(self, text):
        self.details_label.setText(text)    


class App(QMainWindow):
    def __init__(self):
        super().__init__()
        self.settings = Settings()
        self.setWindowTitle("PyChess Pro +")
        self.resize(1550, 950)

        self.game_board = chess.Board()
        self.current_board = self.game_board
        self.is_navigating_history = False
        
        self.engine = None
        self.engine2 = None
        self.is_engine_vs_engine = self.settings.get("game_mode", "human_vs_engine") == "engine_vs_engine"
        self.book = None
        self.analysis_thread = None
        self.game_thread = None
        
        self.human_turn = False
        self.engine_thinking = False
        self.book_move_played = False
        self.is_paused = False
        
        self.eng1_threads = self.settings.get("engine1_threads", 1)
        self.eng2_threads = self.settings.get("engine2_threads", 1)

        self.time_control = self.settings.get("time_control", 300)
        self.increment = self.settings.get("increment", 0)
        self.player_color = chess.WHITE if self.settings.get("player_color") == "white" else chess.BLACK
        self.dark_theme_enabled = self.settings.get("dark_theme", True)
        self.book_max_depth = self.settings.get("book_max_depth", 10)
        
        self.pv_moves_display = self.settings.get("pv_moves_display", 12)
        
        self.current_theme = self.settings.get("theme", "dark_blue")
        self.language = self.settings.get("language", "bg")
        
        self.engine_strength = self.settings.get("engine_strength", "time_based")
        
        # PGN променливи
        self.pgn_file_path = None
        self.pgn_games = []
        self.current_pgn_index = 0
        self.pgn_file_handle = None
        
        # Променлива за проследяване на отворения PGN диалог
        self.pgn_dialog = None
            
        self.set_theme_colors()
            
        self.white_clock = StyledClock("White", self.time_control, "#0078d4", "white")
        self.black_clock = StyledClock("Black", self.time_control, "#d63384", "white")
        
        self.timer = QTimer()
        self.timer.timeout.connect(self.tick_clock)

        self.eval_bar = VerticalEvalBar()
        self.game_chart = SimpleGameChartWidget(main_app=self)
        self.highlights_widget = HighlightsWidget(self)
        
        self.move_evaluations = {}
        self.last_eval = 0
        self.current_move_number = 0
        self.full_game_stack = []
        
        self.apply_theme()
        self.create_menus()
        self.init_ui()
        
        self.load_saved_settings()
        
        self.console = ConsoleWidget(self)
        self.console.hide()
        
        QTimer.singleShot(100, lambda: self.highlights_widget.update_highlights(self.current_board))

    def keyPressEvent(self, event):
        """Прихващане на клавишни комбинации за конзолата"""
        if event.modifiers() == Qt.ControlModifier and event.key() == Qt.Key_QuoteLeft:
            if self.console.isVisible():
                self.console.hide()
            else:
                self.console.show()
                self.console.raise_()
                self.console.activateWindow()
                self.console.input_line.setFocus()
        elif event.modifiers() == Qt.AltModifier and event.key() == Qt.Key_C:
            if not self.console.isVisible():
                self.console.show()
                self.console.raise_()
                self.console.activateWindow()
                self.console.input_line.setFocus()
        else:
            super().keyPressEvent(event)

    def set_theme_colors(self):
        theme = self.current_theme
        
        if theme == "dark_blue":
            self.light_square_color = QColor(216, 222, 233)
            self.dark_square_color = QColor(59, 66, 82)
        elif theme == "classic":
            self.light_square_color = QColor(240, 217, 181)
            self.dark_square_color = QColor(181, 136, 99)
        elif theme == "green":
            self.light_square_color = QColor(234, 240, 206)
            self.dark_square_color = QColor(119, 153, 84)
        elif theme == "blue":
            self.light_square_color = QColor(222, 227, 230)
            self.dark_square_color = QColor(115, 148, 179)
        elif theme == "purple":
            self.light_square_color = QColor(230, 221, 240)
            self.dark_square_color = QColor(136, 84, 153)
        elif theme == "gray":
            self.light_square_color = QColor(220, 220, 220)
            self.dark_square_color = QColor(120, 120, 120)
        else:
            self.light_square_color = QColor(240, 217, 181)
            self.dark_square_color = QColor(181, 136, 99)

    def load_saved_settings(self):
        self.close_engines()
        
        engine1_path = self.settings.get("engine1_path", "")
        if engine1_path and os.path.exists(engine1_path) and HAS_ENGINE:
            try:
                self.engine = chess.engine.SimpleEngine.popen_uci(engine1_path)
                self.engine.configure({"Threads": self.eng1_threads})
            except Exception:
                self.engine = None
                
        engine2_path = self.settings.get("engine2_path", "")
        if engine2_path and os.path.exists(engine2_path) and HAS_ENGINE:
            try:
                self.engine2 = chess.engine.SimpleEngine.popen_uci(engine2_path)
                self.engine2.configure({"Threads": self.eng2_threads})
            except Exception:
                self.engine2 = None
        
        book_path = self.settings.get("book_path", "")
        if book_path and os.path.exists(book_path) and HAS_POLYGLOT:
            try:
                self.book = chess.polyglot.open_reader(book_path)
            except Exception:
                self.book = None
        
        pieces_folder = self.settings.get("pieces_folder", "")
        if pieces_folder and os.path.exists(pieces_folder):
            self.board_w.load_pieces(pieces_folder)
        
        self.board_w.show_engine_arrows = self.settings.get("show_engine_arrows", True)

    def create_menus(self):
        menubar = self.menuBar()
        
        file_menu = menubar.addMenu("Файл" if self.language == "bg" else "File")
        
        new_action = QAction("Нова игра" if self.language == "bg" else "New Game", self)
        new_action.setShortcut("Ctrl+N")
        new_action.triggered.connect(self.new_game)
        file_menu.addAction(new_action)
        
        file_menu.addSeparator()
        
        load_pgn = QAction("Зареди PGN" if self.language == "bg" else "Load PGN", self)
        load_pgn.triggered.connect(self.load_pgn)
        file_menu.addAction(load_pgn)
        
        load_pgn_db = QAction("Отвори PGN база" if self.language == "bg" else "Open PGN Database", self)
        load_pgn_db.triggered.connect(self.load_pgn_database)
        file_menu.addAction(load_pgn_db)
        
        save_pgn = QAction("Запази PGN" if self.language == "bg" else "Save PGN", self)
        save_pgn.triggered.connect(self.save_pgn)
        file_menu.addAction(save_pgn)
        
        save_pgn_db = QAction("Запази като PGN база" if self.language == "bg" else "Save as PGN Database", self)
        save_pgn_db.triggered.connect(self.save_pgn_database)
        file_menu.addAction(save_pgn_db)
        
        file_menu.addSeparator()
        
        pgn_next = QAction("Следваща партия в PGN" if self.language == "bg" else "Next Game in PGN", self)
        pgn_next.triggered.connect(self.next_pgn_game)
        file_menu.addAction(pgn_next)
        
        pgn_prev = QAction("Предишна партия в PGN" if self.language == "bg" else "Previous Game in PGN", self)
        pgn_prev.triggered.connect(self.prev_pgn_game)
        file_menu.addAction(pgn_prev)
        
        file_menu.addSeparator()
        
        exit_action = QAction("Изход" if self.language == "bg" else "Exit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        edit_menu = menubar.addMenu("Редактиране" if self.language == "bg" else "Edit")
        
        pause_action = QAction("Пауза" if self.language == "bg" else "Pause", self)
        pause_action.setShortcut("Space")
        pause_action.triggered.connect(self.toggle_pause)
        edit_menu.addAction(pause_action)
        
        edit_menu.addSeparator()
        
        copy_fen = QAction("Копирай FEN" if self.language == "bg" else "Copy FEN", self)
        copy_fen.triggered.connect(self.copy_fen)
        edit_menu.addAction(copy_fen)
        
        paste_fen = QAction("Постави FEN" if self.language == "bg" else "Paste FEN", self)
        paste_fen.triggered.connect(self.paste_fen)
        edit_menu.addAction(paste_fen)

        engine_menu = menubar.addMenu("Двигател" if self.language == "bg" else "Engine")
        
        load_e1 = QAction("Зареди двигател 1 (Бели)" if self.language == "bg" else "Load Engine 1 (White)", self)
        load_e1.triggered.connect(self.load_engine)
        engine_menu.addAction(load_e1)

        load_e2 = QAction("Зареди двигател 2 (Черни)" if self.language == "bg" else "Load Engine 2 (Black)", self)
        load_e2.triggered.connect(self.load_engine2)
        engine_menu.addAction(load_e2)
        
        engine_menu.addSeparator()
        
        set_e1_thr = QAction("Задай нишки за двигател 1 (1-2)" if self.language == "bg" else "Set Engine 1 Threads (1-2)", self)
        set_e1_thr.triggered.connect(lambda: self.set_threads_dialog(1))
        engine_menu.addAction(set_e1_thr)

        set_e2_thr = QAction("Задай нишки за двигател 2 (1-2)" if self.language == "bg" else "Set Engine 2 Threads (1-2)", self)
        set_e2_thr.triggered.connect(lambda: self.set_threads_dialog(2))
        engine_menu.addAction(set_e2_thr)

        board_menu = menubar.addMenu("Дъска" if self.language == "bg" else "Board")
        
        flip_action = QAction("Обърни дъската" if self.language == "bg" else "Flip Board", self)
        flip_action.triggered.connect(self.flip_board)
        board_menu.addAction(flip_action)
        
        colors_action = QAction("Цветове на дъската" if self.language == "bg" else "Board Colors", self)
        colors_action.triggered.connect(self.open_color_palette)
        board_menu.addAction(colors_action)
        
        board_menu.addSeparator()
        
        toggle_arrows_action = QAction("Покажи стрелки на двигателя" if self.language == "bg" else "Show Engine Arrows", self)
        toggle_arrows_action.setCheckable(True)
        toggle_arrows_action.setChecked(self.settings.get("show_engine_arrows", True))
        toggle_arrows_action.triggered.connect(self.toggle_engine_arrows)
        board_menu.addAction(toggle_arrows_action)

        theme_menu = menubar.addMenu("Теми" if self.language == "bg" else "Themes")
        
        theme_dark_blue = QAction("Тъмно синя тема", self)
        theme_dark_blue.triggered.connect(lambda: self.change_theme("dark_blue"))
        theme_menu.addAction(theme_dark_blue)
        
        theme_classic = QAction("Класическа тема", self)
        theme_classic.triggered.connect(lambda: self.change_theme("classic"))
        theme_menu.addAction(theme_classic)
        
        theme_green = QAction("Зелена тема", self)
        theme_green.triggered.connect(lambda: self.change_theme("green"))
        theme_menu.addAction(theme_green)
        
        theme_blue = QAction("Синя тема", self)
        theme_blue.triggered.connect(lambda: self.change_theme("blue"))
        theme_menu.addAction(theme_blue)
        
        theme_purple = QAction("Лилава тема", self)
        theme_purple.triggered.connect(lambda: self.change_theme("purple"))
        theme_menu.addAction(theme_purple)
        
        theme_gray = QAction("Сива тема", self)
        theme_gray.triggered.connect(lambda: self.change_theme("gray"))
        theme_menu.addAction(theme_gray)

        pieces_menu = menubar.addMenu("Фигури" if self.language == "bg" else "Pieces")
        load_pieces_action = QAction("Зареди фигури" if self.language == "bg" else "Load Pieces", self)
        load_pieces_action.triggered.connect(self.load_pieces)
        pieces_menu.addAction(load_pieces_action)

        book_menu = menubar.addMenu("Отваряне" if self.language == "bg" else "Book")
        load_book = QAction("Зареди отваряне" if self.language == "bg" else "Load Book", self)
        load_book.triggered.connect(self.load_book)
        book_menu.addAction(load_book)

        set_depth = QAction("Максимална дълбочина" if self.language == "bg" else "Set Max Book Depth", self)
        set_depth.triggered.connect(self.set_book_depth)
        book_menu.addAction(set_depth)

        console_menu = menubar.addMenu("Конзола" if self.language == "bg" else "Console")
        
        show_console_action = QAction("Покажи конзолата (Ctrl+`)" if self.language == "bg" else "Show Console (Ctrl+`)", self)
        show_console_action.triggered.connect(lambda: self.console.show())
        console_menu.addAction(show_console_action)
        
        console_menu.addSeparator()
        
        console_help_action = QAction("Помощ за командите" if self.language == "bg" else "Console Commands Help", self)
        console_help_action.triggered.connect(self.show_console_help)
        console_menu.addAction(console_help_action)

        language_menu = menubar.addMenu("Език" if self.language == "bg" else "Language")
        
        bulgarian_action = QAction("Български", self)
        bulgarian_action.triggered.connect(lambda: self.change_language("bg"))
        language_menu.addAction(bulgarian_action)
        
        english_action = QAction("English", self)
        english_action.triggered.connect(lambda: self.change_language("en"))
        language_menu.addAction(english_action)

        help_menu = menubar.addMenu("Помощ" if self.language == "bg" else "Help")
        
        help_action = QAction("Помощ" if self.language == "bg" else "Help", self)
        help_action.triggered.connect(self.show_help)
        help_menu.addAction(help_action)
        
        about_action = QAction("За програмата" if self.language == "bg" else "About", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)

        self.apply_menu_styles(menubar)

    def show_console_help(self):
        """Показва помощ за конзолата"""
        if self.language == "bg":
            help_text = """
╔══════════════════════════════════════════════════════════════╗
║                  КОНЗОЛЕН ИНТЕРФЕЙС - ПОМОЩ                  ║
╠══════════════════════════════════════════════════════════════╣
║                                                              ║
║  Клавишни комбинации:                                        ║
║  • Ctrl+`  - Показва/скрива конзолата                        ║
║  • Alt+C   - Бърз достъп до конзолата                        ║
║  • ↑/↓     - Навигация в историята на командите              ║
║  • Tab     - Автоматично допълване на команди                ║
║  • Enter   - Изпълнява въведената команда                    ║
║                                                              ║
║  Основни команди:                                            ║
║  • help     - Показва този помощен текст                    ║
║  • newgame  - Започва нова игра                             ║
║  • move     - Изпълнява ход (move e2e4)                     ║
║  • undo     - Отменя последния ход                          ║
║  • board    - Показва текущата дъска                        ║
║  • fen      - Показва FEN нотация                           ║
║  • engine   - Контрол на двигателите                        ║
║  • mode     - Промяна на режима на игра                     ║
║  • save     - Запазва играта като PGN                       ║
║  • load     - Зарежда игра от PGN                           ║
║  • history  - Показва история на ходовете                   ║
║  • time     - Показва оставащото време                      ║
║  • pause    - Паузира/продължава играта                     ║
║  • exit     - Затваря конзолата                             ║
║  • quit     - Излиза от програмата                          ║
║  • pgn      - Работа с PGN бази данни                       ║
║                                                              ║
║  За подробна информация за команда: help <име_на_команда>    ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
            """
        else:
            help_text = """
╔══════════════════════════════════════════════════════════════╗
║                  CONSOLE INTERFACE - HELP                    ║
╠══════════════════════════════════════════════════════════════╣
║                                                              ║
║  Keyboard Shortcuts:                                         ║
║  • Ctrl+`  - Show/hide console                              ║
║  • Alt+C   - Quick access to console                        ║
║  • ↑/↓     - Navigation in command history                  ║
║  • Tab     - Command auto-completion                        ║
║  • Enter   - Execute command                                ║
║                                                              ║
║  Basic Commands:                                             ║
║  • help     - Shows this help text                          ║
║  • newgame  - Starts a new game                             ║
║  • move     - Makes a move (move e2e4)                      ║
║  • undo     - Undoes the last move                          ║
║  • board    - Shows current board                           ║
║  • fen      - Shows FEN notation                            ║
║  • engine   - Controls the engines                          ║
║  • mode     - Changes game mode                             ║
║  • save     - Saves game as PGN                             ║
║  • load     - Loads game from PGN                           ║
║  • history  - Shows move history                            ║
║  • time     - Shows remaining time                          ║
║  • pause    - Pauses/resumes the game                       ║
║  • exit     - Closes the console                            ║
║  • quit     - Exits the program                             ║
║  • pgn      - Works with PGN databases                      ║
║                                                              ║
║  For detailed command info: help <command_name>              ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
            """
        
        QMessageBox.information(self, "Конзола - Помощ" if self.language == "bg" else "Console - Help", help_text)
    
    def apply_menu_styles(self, menubar):
        if self.dark_theme_enabled:
            menubar.setStyleSheet("""
                QMenuBar {
                    background-color: #2d2d30;
                    color: white;
                    border: none;
                }
                QMenuBar::item {
                    background-color: transparent;
                    padding: 5px 10px;
                }
                QMenuBar::item:selected {
                    background-color: #505055;
                    border-radius: 3px;
                }
                QMenu {
                    background-color: #2d2d30;
                    color: white;
                    border: 1px solid #555;
                    padding: 5px;
                }
                QMenu::item {
                    padding: 5px 20px 5px 10px;
                }
                QMenu::item:selected {
                    background-color: #0078d4;
                }
                QMenu::separator {
                    background-color: #555;
                    height: 1px;
                    margin: 5px 0px;
                }
            """)
        else:
            menubar.setStyleSheet("""
                QMenuBar {
                    background-color: #f0f0f0;
                    color: black;
                    border: none;
                }
                QMenuBar::item {
                    background-color: transparent;
                    padding: 5px 10px;
                }
                QMenuBar::item:selected {
                    background-color: #e0e0e0;
                    border-radius: 3px;
                }
                QMenu {
                    background-color: #f0f0f0;
                    color: black;
                    border: 1px solid #aaa;
                    padding: 5px;
                }
                QMenu::item {
                    padding: 5px 20px 5px 10px;
                }
                QMenu::item:selected {
                    background-color: #0078d4;
                    color: white;
                }
                QMenu::separator {
                    background-color: #ccc;
                    height: 1px;
                    margin: 5px 0px;
                }
            """)

    def set_book_depth(self):
        val, ok = QInputDialog.getInt(self, 
                                    "Дълбочина на отваряне" if self.language == "bg" else "Book Depth",
                                    "Максимален номер на ход за отваряне:" if self.language == "bg" else "Max move number for book:",
                                    self.book_max_depth, 1, 100)
        if ok:
            self.book_max_depth = val
            self.settings.set("book_max_depth", val)
            self.update_book_info()
            QMessageBox.information(self, 
                                  "Отваряне" if self.language == "bg" else "Book",
                                  f"Отварянето ще се използва до ход {val}." if self.language == "bg" else f"Book will be used until move {val}.")

    def set_threads_dialog(self, eng_num):
        current = self.eng1_threads if eng_num == 1 else self.eng2_threads
        val, ok = QInputDialog.getInt(self, 
                                     f"Двигател {eng_num} нишки" if self.language == "bg" else f"Engine {eng_num} Threads",
                                     "Брой нишки (1-2):" if self.language == "bg" else "Number of Threads (1-2):",
                                     current, 1, 2)
        if ok:
            if eng_num == 1:
                self.eng1_threads = val
                self.settings.set("engine1_threads", val)
                if self.engine:
                    try: 
                        self.engine.configure({"Threads": val})
                    except: 
                        pass
            else:
                self.eng2_threads = val
                self.settings.set("engine2_threads", val)
                if self.engine2:
                    try: 
                        self.engine2.configure({"Threads": val})
                    except: 
                        pass

    def flip_board(self):
        """ВАЖНА КОРЕКЦИЯ: Обръща дъската и ресетва селекцията"""
        self.board_w.flipped = not self.board_w.flipped
        self.board_w.selected = None
        self.board_w.legal_moves_for_selected = []
        self.board_w.update()
        self.update_turn_display()

    def open_color_palette(self):
        dlg = ColorPaletteDialog(self)
        dlg.exec_()

    def toggle_engine_arrows(self, state):
        self.board_w.show_engine_arrows = state
        self.board_w.update()
        self.settings.set("show_engine_arrows", state)

    def change_theme(self, theme_name):
        self.current_theme = theme_name
        self.settings.set("theme", theme_name)
        self.set_theme_colors()
        self.apply_theme()

    def change_language(self, lang):
        self.language = lang
        self.settings.set("language", lang)
        
        if hasattr(self, 'console'):
            self.console.update_command_texts()
            self.console.print_welcome()
        
        QMessageBox.information(self, 
                              "Език" if lang == "bg" else "Language",
                              "Езикът ще се приложи след рестартиране на програмата." if lang == "bg" else "Language will be applied after restarting the program.")

    def show_help(self):
        if self.language == "bg":
            help_text = """
PyChess Pro+ - Помощ

Основни функции:
1. Нова игра - започва нова игра
2. Настройки - промяна на режима, време, теми и др.
3. Двигател - зареждане и конфигуриране на шахматни двигатели
4. Дъска - обръщане на дъската и промяна на цветовете
5. Теми - промяна на визуалната тема
6. Фигури - зареждане на персонализирани фигури
7. Отваряне - работа с бази от отваряния
8. Език - превключване между български и английски
9. Конзола - напреднал контрол през командния ред (Ctrl+`)
10. PGN - работа с PGN файлове и бази данни

Управление:
• Кликване върху фигура за избор
• Кликване върху целево поле за движение
• Двойно кликване за отмяна на избор
• Ctrl+Left - отмяна на ход
• Ctrl+Right - ход напред
• Ctrl+N - нова игра
• Ctrl+Q - изход
• Ctrl+` - показване/скриване на конзолата
• Alt+C - бърз достъп до конзолата

Показване на информация:
• Оценка на позицията (ляво)
• История на ходовете (център)
• Анализ на двигателя (дясно)
• FEN нотация (под дъската)
• Графика на оценката (долу)

Конзолни команди:
• help - показва списък с команди
• move - изпълнява ход (move e2e4)
• board - показва текущата дъска
• engine - контрол на двигателите
• mode - промяна на режима на игра
• pgn - работа с PGN бази данни
            """
        else:
            help_text = """
PyChess Pro+ - Help

Main features:
1. New Game - start a new game
2. Settings - change mode, time, themes, etc.
3. Engine - load and configure chess engines
4. Board - flip board and change colors
5. Themes - change visual theme
6. Pieces - load custom pieces
7. Book - work with opening books
8. Language - switch between Bulgarian and English
9. Console - advanced control via command line (Ctrl+`)
10. PGN - work with PGN files and databases

Controls:
• Click on a piece to select
• Click on target square to move
• Double click to cancel selection
• Ctrl+Left - undo move
• Ctrl+Right - redo move
• Ctrl+N - new game
• Ctrl+Q - exit
• Ctrl+` - show/hide console
• Alt+C - quick access to console

Information display:
• Position evaluation (left)
• Move history (center)
• Engine analysis (right)
• FEN notation (below board)
• Evaluation chart (bottom)

Console commands:
• help - shows command list
• move - makes a move (move e2e4)
• board - shows current board
• engine - controls the engines
• mode - changes game mode
• pgn - works with PGN databases
            """
        
        QMessageBox.information(self, "Помощ" if self.language == "bg" else "Help", help_text)

    def show_about(self):
        about_text = """
PyChess Pro+ v1.0

Написано на Python с PyQt5
Използва библиотека python-chess

Функции:
• Игра срещу двигател
• Двигател срещу двигател
• Анализ на позиции
• Отваряния (Polyglot)
• Персонализирани теми и фигури
• Пълна история на ходовете
• Графика на оценката
• Многоезична поддръжка
• Конзолен интерфейс за напреднали
• PGN файлове и бази данни

© 2024 PyChess Pro+ Team
        """
        
        QMessageBox.about(self, "За PyChess Pro+" if self.language == "bg" else "About PyChess Pro+", about_text)

    def apply_theme(self):
        is_dark_theme = self.current_theme in ["dark_blue"]
        
        if is_dark_theme:
            self.setStyleSheet("""
                QMainWindow { 
                    background-color: #202020; 
                    color: #ffffff; 
                }
                QWidget { 
                    background-color: #202020; 
                    color: #ffffff; 
                }
                /* СТИЛОВЕ ЗА ТАБЛИЦАТА ЗА ИСТОРИЯ НА ХОДОВЕТЕ */
                QTableWidget {
                    background-color: #1e1e1e;
                    color: #ffffff;
                    border: 1px solid #444;
                    gridline-color: #444;
                    selection-background-color: #0078d4;
                    selection-color: white;
                }
                QTableWidget::item {
                    background-color: #2d2d30;
                    color: #ffffff;
                    border-bottom: 1px solid #444;
                }
                QTableWidget::item:selected {
                    background-color: #0078d4;
                    color: white;
                }
                QHeaderView::section {
                    background-color: #3e3e42;
                    color: #ffffff;
                    border: 1px solid #444;
                    padding: 5px;
                    font-weight: bold;
                }
                QHeaderView {
                    background-color: #3e3e42;
                }
                /* КРАЙ НА СТИЛОВЕТЕ ЗА ТАБЛИЦАТА */
                QGroupBox { 
                    border: 1px solid #444; 
                    margin-top: 10px; 
                    border-radius: 8px; 
                    font-weight: bold; 
                    color: #eee;
                    background-color: #2d2d30;
                    padding-top: 10px;
                }
                QGroupBox::title { 
                    subcontrol-origin: margin; 
                    left: 10px; 
                    padding: 0 5px; 
                }
                QPushButton { 
                    background-color: #3e3e42; 
                    color: white; 
                    border-radius: 6px; 
                    padding: 6px;
                    border: none;
                    font-weight: 500;
                }
                QPushButton:hover { 
                    background-color: #505055; 
                }
                QPushButton:checked { 
                    background-color: #0078d4; 
                } 
                QPushButton:pressed { 
                    background-color: #005a9e; 
                }
                QListWidget { 
                    background-color: #1e1e1e; 
                    color: white; 
                    border: 1px solid #444; 
                    border-radius: 4px; 
                    selection-background-color: #0078d4;
                }
                QTextEdit { 
                    background-color: #1e1e1e; 
                    color: #00ff00;
                    border: 1px solid #444; 
                    border-radius: 4px;
                    font-family: 'Consolas', monospace; 
                    font-size: 13px;
                    line-height: 1.4;
                    padding: 10px;
                }
                QLabel { 
                    color: #f0f0f0; 
                }
                QComboBox, QDoubleSpinBox, QSpinBox {
                    background-color: #3e3e42;
                    color: white;
                    border: 1px solid #555;
                    border-radius: 4px;
                    padding: 2px;
                }
                QSplitter::handle {
                    background-color: #444;
                }
            """)
            self.white_clock.base_color = "#0078d4"
            self.black_clock.base_color = "#d63384"
            self.white_clock.text_color = "white"
            self.black_clock.text_color = "white"
            
            if hasattr(self, 'program_title'):
                self.program_title.setStyleSheet("color: #ffffff; font-size: 24px; font-weight: bold; background: transparent; padding: 10px;")
        else:
            self.setStyleSheet("""
                QMainWindow { 
                    background:#f4f1ec 
                }
                QWidget { 
                    background-color: #f4f1ec; 
                    color: black; 
                }
                /* СТИЛОВЕ ЗА ТАБЛИЦАТА ЗА ИСТОРИЯ НА ХОДОВЕТЕ В СВЕТЛА ТЕМА */
                QTableWidget {
                    background-color: white;
                    color: black;
                    border: 1px solid #aaa;
                    gridline-color: #ccc;
                    selection-background-color: #0078d4;
                    selection-color: white;
                }
                QTableWidget::item {
                    background-color: white;
                    color: black;
                    border-bottom: 1px solid #ddd;
                }
                QTableWidget::item:selected {
                    background-color: #0078d4;
                    color: white;
                }
                QHeaderView::section {
                    background-color: #f0f0f0;
                    color: black;
                    border: 1px solid #aaa;
                    padding: 5px;
                    font-weight: bold;
                }
                QHeaderView {
                    background-color: #f0f0f0;
                }
                /* КРАЙ НА СТИЛОВЕТЕ ЗА ТАБЛИЦАТА */
                QGroupBox { 
                    font-weight: bold; 
                    border: 1px solid #aaa; 
                    margin-top: 5px; 
                    border-radius: 5px; 
                    background-color: white;
                }
                QGroupBox::title { 
                    subcontrol-origin: margin; 
                    left: 10px; 
                    padding: 0 3px; 
                }
                QPushButton { 
                    padding: 5px; 
                    border-radius: 4px; 
                    background-color: #e0e0e0; 
                    color: black;
                }
                QPushButton:hover { 
                    background-color: #d0d0d0; 
                }
                QTextEdit { 
                    font-family: 'Consolas', monospace; 
                    font-size: 13px;
                    line-height: 1.4;
                    padding: 10px;
                    background-color: white;
                    color: black;
                    border: 1px solid #ccc;
                }
                QListWidget {
                    background-color: white;
                    color: black;
                    border: 1px solid #ccc;
                }
                QSplitter::handle {
                    background-color: #ddd;
                }
            """)
            self.white_clock.base_color = "#5bc0de"
            self.black_clock.base_color = "#5cb85c"
            self.white_clock.text_color = "white"
            self.black_clock.text_color = "white"
            
            if hasattr(self, 'program_title'):
                self.program_title.setStyleSheet("color: #000000; font-size: 24px; font-weight: bold; background: transparent; padding: 10px;")

        if hasattr(self, 'white_clock'): 
            self.white_clock.init_style()
        if hasattr(self, 'black_clock'): 
            self.black_clock.init_style()
        if hasattr(self, 'board_w'): 
            self.board_w.update()
        
        if hasattr(self, 'fen_label'):
            if is_dark_theme:
                self.fen_label.setStyleSheet("padding: 3px; background: #2d2d30; color: #f0f0f0; border: 1px solid #555; border-radius: 3px;")
            else:
                self.fen_label.setStyleSheet("padding: 3px; background: #f0f0f0; color: #000000; border: 1px solid #ccc; border-radius: 3px;")

    def close_engines(self):
        """Затваряне на всички двигатели и изчистване на паметта"""
        if self.engine:
            try:
                self.engine.quit()
                self.engine.close()
                self.engine = None
            except:
                pass
                self.engine = None
        
        if self.engine2:
            try:
                self.engine2.quit()
                self.engine2.close()
                self.engine2 = None
            except:
                pass
                self.engine2 = None
        
        if self.analysis_thread and self.analysis_thread.isRunning():
            self.analysis_thread.stop()
            self.analysis_thread.wait(2000)
            self.analysis_thread = None
        
        if self.game_thread and self.game_thread.isRunning():
            self.game_thread.stop()
            self.game_thread.wait(2000)
            self.game_thread = None

    def closeEvent(self, event):
        self.timer.stop()
        self.stop_analysis()
        self.close_engines()
        
        # Затваряне на PGN диалога, ако е отворен
        if self.pgn_dialog:
            try:
                self.pgn_dialog.close()
            except:
                pass
            self.pgn_dialog = None
            
        self.settings.save()
        
        if self.book:
            try: 
                self.book.close()
            except: 
                pass
        
        # Затваряне на PGN файла, ако е отворен
        if self.pgn_file_handle:
            try:
                self.pgn_file_handle.close()
            except:
                pass
            
        event.accept()

    def init_ui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        
        main_splitter = QSplitter(Qt.Horizontal)
        
        left_panel_widget = QWidget()
        left_panel = QVBoxLayout(left_panel_widget)
        left_panel.setSpacing(5)
        left_panel.setContentsMargins(0, 0, 0, 0)

        clock_container = QWidget()
        clock_layout = QHBoxLayout(clock_container)
        clock_layout.setSpacing(10)
        clock_layout.setContentsMargins(0, 0, 0, 0)
        clock_layout.addStretch()
        clock_layout.addWidget(self.white_clock)
        clock_layout.addWidget(self.black_clock)
        clock_layout.addStretch()
        left_panel.addWidget(clock_container)

        board_container = QHBoxLayout()
        board_container.setSpacing(2)
        board_container.setContentsMargins(0, 0, 0, 0)
        
        self.board_w = BoardWidget(self)
        self.board_w.human_move.connect(self.human_move)
        board_container.addWidget(self.board_w)
        board_container.addWidget(self.eval_bar)
        
        left_panel.addLayout(board_container)
        
        info_container = QWidget()
        info_layout = QVBoxLayout(info_container)
        
        fen_label_title = QLabel("FEN:")
        fen_label_title.setFont(QFont("Arial", 9, QFont.Bold))
        info_layout.addWidget(fen_label_title)
        
        self.fen_label = QLabel(self.current_board.fen())
        self.fen_label.setFont(QFont("Consolas", 8))
        self.fen_label.setWordWrap(True)
        info_layout.addWidget(self.fen_label)
        
        # PGN информация
        pgn_info_container = QWidget()
        pgn_info_layout = QHBoxLayout(pgn_info_container)
        
        self.pgn_info_label = QLabel("")
        self.pgn_info_label.setFont(QFont("Arial", 9))
        self.pgn_info_label.setWordWrap(True)
        pgn_info_layout.addWidget(self.pgn_info_label)
        
        info_layout.addWidget(pgn_info_container)
        
        self.program_title = QLabel("PyChess Pro+")
        self.program_title.setAlignment(Qt.AlignCenter)
        self.program_title.setFont(QFont("Arial", 24, QFont.Bold))
        info_layout.addWidget(self.program_title)
        
        left_panel.addWidget(info_container)

        middle_panel_widget = QWidget()
        middle_panel = QVBoxLayout(middle_panel_widget)
        middle_panel.setSpacing(5)
        middle_panel.setContentsMargins(0, 0, 0, 0)
        
        top_middle_splitter = QSplitter(Qt.Vertical)
        
        move_group = QWidget()
        move_layout = QVBoxLayout(move_group)
        
        move_title = QLabel("История на ходовете" if self.language == "bg" else "Move History")
        move_title.setFont(QFont("Arial", 12, QFont.Bold))
        move_title.setStyleSheet("color: #ffffff; background: #0078d4; padding: 8px; border-radius: 6px;")
        move_title.setAlignment(Qt.AlignCenter)
        move_layout.addWidget(move_title)
        
        self.engine_turn_label = QLabel()
        self.engine_turn_label.setFixedHeight(40)
        self.engine_turn_label.setAlignment(Qt.AlignCenter)
        self.engine_turn_label.setFont(QFont("Arial", 12, QFont.Bold))
        self.engine_turn_label.setStyleSheet("""
            QLabel {
                color: #ffffff;
                background-color: #0078d4;
                border-radius: 6px;
                border: 2px solid #005a9e;
                padding: 5px;
            }
        """)
        move_layout.addWidget(self.engine_turn_label)
        
        self.move_table = QTableWidget()
        self.move_table.setColumnCount(3)
        self.move_table.setHorizontalHeaderLabels(["№", "Бели", "Черни"])
        self.move_table.horizontalHeader().setStretchLastSection(True)
        self.move_table.verticalHeader().setVisible(False)
        self.move_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.move_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.move_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.move_table.setFont(QFont("Consolas", 12, QFont.Bold))
        self.move_table.itemClicked.connect(self.history_clicked_safe)
        
        self.move_table.setStyleSheet("""
            QTableWidget {
                background-color: #1e1e1e;
                color: #e0e0e0;
                border: 1px solid #444;
                gridline-color: #444;
            }
            QTableWidget::item {
                background-color: #2d2d30;
                color: #ffffff;
                border-bottom: 1px solid #444;
            }
            QTableWidget::item:selected {
                background-color: #0078d4;
                color: white;
            }
            QHeaderView::section {
                background-color: #3e3e42;
                color: #ffffff;
                border: 1px solid #444;
                padding: 5px;
                font-weight: bold;
            }
        """)
        
        self.move_table.horizontalHeader().setDefaultAlignment(Qt.AlignCenter)
        
        move_layout.addWidget(self.move_table)
        
        book_group = QWidget()
        book_layout = QVBoxLayout(book_group)
        
        book_title = QLabel("Отваряния" if self.language == "bg" else "Book Moves")
        book_title.setFont(QFont("Arial", 12, QFont.Bold))
        book_title.setStyleSheet("color: #ffffff; background: #28a745; padding: 8px; border-radius: 6px;")
        book_title.setAlignment(Qt.AlignCenter)
        book_layout.addWidget(book_title)
        
        self.book_list = QListWidget()
        self.book_list.setFont(QFont("Consolas", 12, QFont.Bold))
        self.book_list.itemDoubleClicked.connect(self.show_book_details)
        book_layout.addWidget(self.book_list)
        
        top_middle_splitter.addWidget(move_group)
        top_middle_splitter.addWidget(book_group)
        
        chart_group = QGroupBox("Графика на оценката" if self.language == "bg" else "Game Evaluation Chart")
        chart_layout = QVBoxLayout(chart_group)
        chart_layout.addWidget(self.game_chart)
        
        middle_panel.addWidget(top_middle_splitter, 3)
        middle_panel.addWidget(chart_group, 2)

        right_panel_widget = QWidget()
        right_panel = QVBoxLayout(right_panel_widget)
        right_panel.setSpacing(10)
        right_panel.setContentsMargins(0, 0, 0, 0)
        
        right_splitter = QSplitter(Qt.Vertical)
        
        controls_group = QGroupBox("Контроли" if self.language == "bg" else "Controls")
        controls_layout = QVBoxLayout()
        
        main_btn_layout = QHBoxLayout()
        self.btn_new = QPushButton("Нова игра" if self.language == "bg" else "New Game")
        self.btn_new.setFont(QFont("Arial", 10, QFont.Bold))
        self.btn_new.setFixedHeight(35)
        self.btn_new.clicked.connect(self.new_game)
        
        self.btn_settings = QPushButton("Настройки" if self.language == "bg" else "Settings")
        self.btn_settings.setFont(QFont("Arial", 10, QFont.Bold))
        self.btn_settings.setFixedHeight(35)
        self.btn_settings.clicked.connect(self.open_settings)
        
        main_btn_layout.addWidget(self.btn_new)
        main_btn_layout.addWidget(self.btn_settings)
        controls_layout.addLayout(main_btn_layout)

        pause_layout = QHBoxLayout()
        pause_layout.setSpacing(5)
        self.btn_pause = QPushButton("Пауза" if self.language == "bg" else "Pause")
        self.btn_pause.setFont(QFont("Arial", 10, QFont.Bold))
        self.btn_pause.setFixedHeight(35)
        self.btn_pause.clicked.connect(self.toggle_pause)
        pause_layout.addWidget(self.btn_pause)
        controls_layout.addLayout(pause_layout)
        
        undo_layout = QHBoxLayout()
        undo_layout.setSpacing(5)
        self.btn_undo = QPushButton("Отмени ход" if self.language == "bg" else "Undo Move")
        self.btn_undo.setFont(QFont("Arial", 10, QFont.Bold))
        self.btn_undo.setFixedHeight(35)
        self.btn_undo.clicked.connect(self.undo_move)
        undo_layout.addWidget(self.btn_undo)
        controls_layout.addLayout(undo_layout)
        
        draw_layout = QHBoxLayout()
        draw_layout.setSpacing(5)
        self.btn_draw = QPushButton("Предложи реми" if self.language == "bg" else "Offer Draw")
        self.btn_draw.setFont(QFont("Arial", 10, QFont.Bold))
        self.btn_draw.setFixedHeight(35)
        self.btn_draw.clicked.connect(self.offer_draw)
        draw_layout.addWidget(self.btn_draw)
        controls_layout.addLayout(draw_layout)
        
        # PGN навигация
        pgn_nav_layout = QHBoxLayout()
        pgn_nav_layout.setSpacing(5)
        
        self.btn_pgn_prev = QPushButton("← PGN" if self.language == "bg" else "← PGN")
        self.btn_pgn_prev.setFont(QFont("Arial", 10, QFont.Bold))
        self.btn_pgn_prev.setFixedHeight(35)
        self.btn_pgn_prev.clicked.connect(self.prev_pgn_game)
        self.btn_pgn_prev.setEnabled(False)
        
        self.btn_pgn_next = QPushButton("PGN →" if self.language == "bg" else "PGN →")
        self.btn_pgn_next.setFont(QFont("Arial", 10, QFont.Bold))
        self.btn_pgn_next.setFixedHeight(35)
        self.btn_pgn_next.clicked.connect(self.next_pgn_game)
        self.btn_pgn_next.setEnabled(False)
        
        pgn_nav_layout.addWidget(self.btn_pgn_prev)
        pgn_nav_layout.addWidget(self.btn_pgn_next)
        controls_layout.addLayout(pgn_nav_layout)

        # Преки пътища (Shortcuts)
        self.shortcut_undo = QShortcut(QKeySequence("Ctrl+Left"), self)
        self.shortcut_undo.activated.connect(self.undo_move)
        
        self.shortcut_redo = QShortcut(QKeySequence("Ctrl+Right"), self)
        self.shortcut_redo.activated.connect(self.redo_move)
        
        self.shortcut_pgn_prev = QShortcut(QKeySequence("Ctrl+Shift+Left"), self)
        self.shortcut_pgn_prev.activated.connect(self.prev_pgn_game)
        
        self.shortcut_pgn_next = QShortcut(QKeySequence("Ctrl+Shift+Right"), self)
        self.shortcut_pgn_next.activated.connect(self.next_pgn_game)

        controls_group.setLayout(controls_layout)
        
        self.analysis_group = QGroupBox("Анализ на двигателя" if self.language == "bg" else "Engine Analysis")
        analysis_layout = QVBoxLayout()
        
        stats_layout = QGridLayout()
        
        self.depth_label = QLabel("Дълбочина: 0" if self.language == "bg" else "Depth: 0")
        self.depth_label.setFont(QFont("Segoe UI", 11, QFont.Bold))
        self.depth_label.setFixedHeight(30)
        self.depth_label.setAlignment(Qt.AlignCenter)
        self.depth_label.setStyleSheet("color: #00aaff; padding: 0 5px;")
        self.depth_label.setMinimumWidth(120)
        
        self.eval_label = QLabel("Оценка: 0.00" if self.language == "bg" else "Eval: 0.00")
        self.eval_label.setFont(QFont("Segoe UI", 11, QFont.Bold))
        self.eval_label.setFixedHeight(30)
        self.eval_label.setAlignment(Qt.AlignCenter)
        self.eval_label.setStyleSheet("color: #ffaa00; padding: 0 5px;")
        self.eval_label.setMinimumWidth(120)
        
        self.nodes_label = QLabel("Позиции: 0" if self.language == "bg" else "Nodes: 0")
        self.nodes_label.setFont(QFont("Segoe UI", 11, QFont.Bold))
        self.nodes_label.setFixedHeight(30)
        self.nodes_label.setAlignment(Qt.AlignCenter)
        self.nodes_label.setStyleSheet("color: #00ffaa; padding: 0 5px;")
        self.nodes_label.setMinimumWidth(120)
        
        stats_layout.addWidget(self.depth_label, 0, 0)
        stats_layout.addWidget(self.eval_label, 0, 1)
        stats_layout.addWidget(self.nodes_label, 0, 2)
        
        stats_layout.setColumnStretch(0, 1)
        stats_layout.setColumnStretch(1, 1)
        stats_layout.setColumnStretch(2, 1)
        
        analysis_layout.addLayout(stats_layout)
        
        pv_group = QGroupBox("Основна вариация" if self.language == "bg" else "Principal Variation")
        pv_layout = QVBoxLayout()
        
        self.pv_text = QTextEdit()
        self.pv_text.setReadOnly(True)
        self.pv_text.setFont(QFont("Consolas", 11, QFont.Bold))
        self.pv_text.setStyleSheet("""
            background: #1a1a1a; 
            color: #ffffff;
            line-height: 1.5;
            border: 2px solid #444;
            border-radius: 8px;
            padding: 10px;
            font-weight: bold;
        """)
        self.pv_text.setMinimumHeight(200)
        
        pv_layout.addWidget(self.pv_text)
        pv_group.setLayout(pv_layout)
        
        analysis_layout.addWidget(pv_group)
        self.analysis_group.setLayout(analysis_layout)
        
        highlights_group = QGroupBox("Статистика на позицията" if self.language == "bg" else "Position Highlights")
        highlights_layout = QVBoxLayout()
        highlights_layout.addWidget(self.highlights_widget)
        highlights_group.setLayout(highlights_layout)
        
        right_splitter.addWidget(controls_group)
        right_splitter.addWidget(self.analysis_group)
        right_splitter.addWidget(highlights_group)
        
        right_splitter.setSizes([100, 350, 200])
        
        right_panel.addWidget(right_splitter)

        main_splitter.addWidget(left_panel_widget)
        main_splitter.addWidget(middle_panel_widget)
        main_splitter.addWidget(right_panel_widget)
        
        main_splitter.setSizes([500, 450, 450])
        
        main_layout = QHBoxLayout(main_widget)
        main_layout.addWidget(main_splitter)
        
        self.update_turn_display()
        self.update_pgn_info()

    def update_turn_display(self):
        """ВАЖНА КОРЕКЦИЯ: Актуализира показването на кой е на ход"""
        if self.is_engine_vs_engine:
            if self.current_board.turn == chess.WHITE:
                engine_path = self.settings.get("engine1_path", "")
                if engine_path:
                    engine_name = os.path.basename(engine_path)
                else:
                    engine_name = "No engine (White)"
                if self.language == "bg":
                    text = f"{engine_name} на ход (Бели)"
                else:
                    text = f"{engine_name} to move (White)"
            else:
                engine_path = self.settings.get("engine2_path", "")
                if engine_path:
                    engine_name = os.path.basename(engine_path)
                else:
                    engine_name = "No engine (Black)"
                if self.language == "bg":
                    text = f"{engine_name} на ход (Черни)"
                else:
                    text = f"{engine_name} to move (Black)"
        else:
            if self.current_board.turn == self.player_color:
                if self.language == "bg":
                    color = "Бели" if self.player_color == chess.WHITE else "Черни"
                    text = f"Вашият ход ({color})"
                else:
                    color = "White" if self.player_color == chess.WHITE else "Black"
                    text = f"Your turn ({color})"
            else:
                engine_path = self.settings.get("engine1_path", "")
                if engine_path:
                    engine_name = os.path.basename(engine_path)
                else:
                    engine_name = "No engine"
                
                if self.language == "bg":
                    color = "Бели" if self.current_board.turn == chess.WHITE else "Черни"
                    text = f"{engine_name} на ход ({color})"
                else:
                    color = "White" if self.current_board.turn == chess.WHITE else "Black"
                    text = f"{engine_name} to move ({color})"
        
        self.engine_turn_label.setText(text)
        
        if self.current_board.turn == chess.WHITE:
            self.engine_turn_label.setStyleSheet("""
                QLabel {
                    color: #ffffff;
                    background-color: #0078d4;
                    border-radius: 6px;
                    border: 2px solid #005a9e;
                    padding: 5px;
                }
            """)
        else:
            self.engine_turn_label.setStyleSheet("""
                QLabel {
                    color: #ffffff;
                    background-color: #d63384;
                    border-radius: 6px;
                    border: 2px solid #a02d66;
                    padding: 5px;
                }
            """)

    def update_pgn_info(self):
        """Обновява информацията за текущо отворения PGN файл"""
        if self.pgn_file_path and self.pgn_games:
            game_count = len(self.pgn_games)
            current_game = self.current_pgn_index + 1
            
            if self.language == "bg":
                info = f"PGN: {os.path.basename(self.pgn_file_path)} | Партия {current_game}/{game_count}"
            else:
                info = f"PGN: {os.path.basename(self.pgn_file_path)} | Game {current_game}/{game_count}"
            
            self.pgn_info_label.setText(info)
            self.btn_pgn_prev.setEnabled(self.current_pgn_index > 0)
            self.btn_pgn_next.setEnabled(self.current_pgn_index < len(self.pgn_games) - 1)
        else:
            self.pgn_info_label.setText("")
            self.btn_pgn_prev.setEnabled(False)
            self.btn_pgn_next.setEnabled(False)

    def show_book_details(self, item):
        if not HAS_POLYGLOT or not self.book:
            return
            
        try:
            entries = list(self.book.find_all(self.game_board))
            if not entries:
                return
                
            entries = list(entries)
            entries.sort(key=lambda x: x.weight, reverse=True)
            total_weight = sum(e.weight for e in entries)
            
            dlg = BookDisplayDialog(self, entries, total_weight)
            dlg.exec_()
        except Exception:
            pass

    def history_clicked_safe(self, item):
        if self.is_engine_vs_engine and (self.game_thread and self.game_thread.isRunning()):
            QMessageBox.warning(self, "Внимание" if self.language == "bg" else "Warning", 
                               "Не може да навигирате история по време на игра двигател срещу двигател." if self.language == "bg" else "Cannot navigate history during engine-vs-engine game.")
            return
            
        row = item.row()
        col = item.column()
        
        # Индекс на хода в move_stack
        # Ред 0, Кол 1 -> Ход 0 (Бели)
        # Ред 0, Кол 2 -> Ход 1 (Черни)
        # Ред 1, Кол 1 -> Ход 2 (Бели)
        
        move_index = -1
        if col == 1:
            move_index = row * 2
        elif col == 2:
            move_index = row * 2 + 1
            
        if move_index >= 0 and move_index < len(self.game_board.move_stack):
            self.navigate_to_move(move_index)

    def navigate_to_move(self, index):
        """Навигация до конкретен ход в историята"""
        self.stop_engine_thread()
        self.stop_analysis()
        
        # Създаваме временно табло до този ход
        temp_board = chess.Board()
        # Ако играта не започва от начална позиция, трябва да се съобрази
        if self.game_board.move_stack:
            try:
                temp_board.set_fen(self.game_board.move_stack[0].board().fen())
            except:
                pass
                
        for i in range(index + 1):
            temp_board.push(self.game_board.move_stack[i])
            
        self.current_board = temp_board
        self.is_navigating_history = True
        self.current_move_number = index + 1
        
        self.board_w.last_move = self.game_board.move_stack[index]
        self.board_w.update()
        self.fen_label.setText(self.current_board.fen())
        self.highlights_widget.update_highlights(self.current_board)
        self.update_turn_display()
        
        QTimer.singleShot(100, self.start_analysis)

    def play_sound(self, name):
        try:
            path = f"sounds/{name}.wav"
            if os.path.exists(path):
                try:
                    from PyQt5.QtMultimedia import QSoundEffect
                    effect = QSoundEffect()
                    effect.setSource(QUrl.fromLocalFile(os.path.abspath(path)))
                    effect.play()
                except Exception:
                    pass
        except Exception:
            pass

    def load_pieces(self):
        d = QFileDialog.getExistingDirectory(self, "Папка с фигури" if self.language == "bg" else "Pieces folder")
        if d:
            self.board_w.load_pieces(d)
            self.board_w.update()
            self.settings.set("pieces_folder", d)

    def load_engine(self):
        if not HAS_ENGINE: 
            return
        p, _ = QFileDialog.getOpenFileName(self, "UCI двигател (Бели)" if self.language == "bg" else "UCI Engine (White)")
        if p:
            try:
                self.close_engines()
                self.engine = chess.engine.SimpleEngine.popen_uci(p)
                self.engine.configure({"Threads": self.eng1_threads})
                self.settings.set("engine1_path", p)
                QMessageBox.information(self, "Двигател" if self.language == "bg" else "Engine", "Двигател 1 зареден!" if self.language == "bg" else "Engine 1 loaded!")
                if not self.is_engine_vs_engine and self.game_board.turn != self.player_color:
                    self.start_analysis()
                self.update_turn_display()
            except Exception as e:
                QMessageBox.warning(self, "Грешка" if self.language == "bg" else "Error", 
                                  f"Грешка при зареждане на двигател: {e}" if self.language == "bg" else f"Could not load engine: {e}")

    def load_engine2(self):
        if not HAS_ENGINE: 
            return
        p, _ = QFileDialog.getOpenFileName(self, "UCI двигател (Черни)" if self.language == "bg" else "UCI Engine (Black)")
        if p:
            try:
                self.close_engines()
                self.engine2 = chess.engine.SimpleEngine.popen_uci(p)
                self.engine2.configure({"Threads": self.eng2_threads})
                self.settings.set("engine2_path", p)
                QMessageBox.information(self, "Двигател" if self.language == "bg" else "Engine", "Двигател 2 зареден!" if self.language == "bg" else "Engine 2 loaded!")
                self.update_turn_display()
            except Exception as e:
                QMessageBox.warning(self, "Грешка" if self.language == "bg" else "Error", 
                                  f"Грешка при зареждане на двигател: {e}" if self.language == "bg" else f"Could not load engine: {e}")

    def load_book(self):
        p, _ = QFileDialog.getOpenFileName(self, "Polyglot отваряне" if self.language == "bg" else "Polyglot Book", filter="*.bin")
        if p:
            try:
                if self.book:
                    try:
                        self.book.close()
                    except Exception:
                        pass
                    self.book = None
                
                time.sleep(0.1)
                
                self.book = chess.polyglot.open_reader(p)
                self.settings.set("book_path", p)
                
                try:
                    list(self.book.find_all(chess.Board()))[:1]
                    self.update_book_info()
                    QMessageBox.information(self, "Отваряне" if self.language == "bg" else "Book", 
                                          f"Отварянето е заредено успешно!\nЩе се използва до ход {self.book_max_depth}." if self.language == "bg" else f"Book loaded successfully!\nWill be used until move {self.book_max_depth}.")
                except Exception as e:
                    QMessageBox.warning(self, "Грешка" if self.language == "bg" else "Error", 
                                      f"Файлът с отваряне може да е повреден: {e}" if self.language == "bg" else f"Book file might be corrupted: {e}")
                    self.book = None
                    
            except OSError as e:
                QMessageBox.warning(self, "Грешка в отварянето" if self.language == "bg" else "Book Error", 
                                   f"Грешка при достъп до файл с отваряне:\n{str(e)}" if self.language == "bg" else f"Could not access book file:\n{str(e)}")
                self.book = None
                self.update_book_info()
            except Exception as e:
                QMessageBox.warning(self, "Грешка" if self.language == "bg" else "Error", 
                                  f"Грешка при зареждане на отваряне: {e}" if self.language == "bg" else f"Could not load book: {e}")
                self.book = None
                self.update_book_info()

    def update_book_info(self):
        self.book_list.clear()
        
        if not HAS_POLYGLOT:
            self.book_list.addItem("Липсва библиотека 'chess.polyglot'" if self.language == "bg" else "Missing 'chess.polyglot' library")
            return

        if self.book is None:
            self.book_list.addItem("Няма заредено отваряне" if self.language == "bg" else "No book loaded")
            return

        try:
            entries = list(self.book.find_all(self.game_board))
            if not entries:
                self.book_list.addItem("Няма отваряния" if self.language == "bg" else "No book moves")
                return

            entries = list(entries)
            entries.sort(key=lambda x: x.weight, reverse=True)
            total_weight = sum(e.weight for e in entries)
            
            for entry in entries[:12]:
                if entry.move in self.game_board.legal_moves:
                    san = self.game_board.san(entry.move)
                    percent = (entry.weight / total_weight) * 100
                    move_info = f"{san:8s} - {percent:5.1f}% ({entry.weight})"
                    self.book_list.addItem(move_info)
            
        except Exception as e:
            self.book_list.addItem(f"Грешка: {str(e)[:50]}" if self.language == "bg" else f"Error: {str(e)[:50]}")

    def open_settings(self):
        dlg = QDialog(self)
        dlg.setWindowTitle("Настройки на играта" if self.language == "bg" else "Game Settings")
        dlg.resize(400, 500)
        layout = QFormLayout(dlg)
        
        mode_combo = QComboBox()
        mode_combo.addItems(["Човек срещу двигател" if self.language == "bg" else "Human vs Engine", 
                           "Двигател срещу двигател" if self.language == "bg" else "Engine vs Engine"])
        mode_combo.setCurrentText("Двигател срещу двигател" if self.language == "bg" and self.is_engine_vs_engine else 
                                "Engine vs Engine" if self.is_engine_vs_engine else 
                                "Човек срещу двигател" if self.language == "bg" else "Human vs Engine")
        layout.addRow("Режим на игра:" if self.language == "bg" else "Game Mode:", mode_combo)
        
        color_combo = QComboBox()
        color_combo.addItems(["Бели" if self.language == "bg" else "White", 
                            "Черни" if self.language == "bg" else "Black", 
                            "Случайно" if self.language == "bg" else "Random"])
        if hasattr(self, 'player_color'):
            current_color = "Бели" if self.player_color == chess.WHITE and self.language == "bg" else "White" if self.player_color == chess.WHITE else "Черни" if self.language == "bg" else "Black"
            color_combo.setCurrentText(current_color)
        layout.addRow("Играеш като:" if self.language == "bg" else "Play as:", color_combo)
        
        engine_limit_combo = QComboBox()
        engine_limit_combo.addItems(["Въз основа на време (TC)" if self.language == "bg" else "Time based (TC)",
                                   "Дълбочина 15 (Стандарт)" if self.language == "bg" else "Depth 15 (Standard)",
                                   "Дълбочина 20 (Силно)" if self.language == "bg" else "Depth 20 (Strong)",
                                   "Дълбочина 10 (Бързо)" if self.language == "bg" else "Depth 10 (Fast)",
                                   "Позиции 1000000" if self.language == "bg" else "Nodes 1000000"])
        current_strength = self.settings.get("engine_strength", "time_based")
        if current_strength == "time_based":
            engine_limit_combo.setCurrentText("Въз основа на време (TC)" if self.language == "bg" else "Time based (TC)")
        elif current_strength == "depth_15":
            engine_limit_combo.setCurrentText("Дълбочина 15 (Стандарт)" if self.language == "bg" else "Depth 15 (Standard)")
        elif current_strength == "depth_20":
            engine_limit_combo.setCurrentText("Дълбочина 20 (Силно)" if self.language == "bg" else "Depth 20 (Strong)")
        elif current_strength == "depth_10":
            engine_limit_combo.setCurrentText("Дълбочина 10 (Бързо)" if self.language == "bg" else "Depth 10 (Fast)")
        elif current_strength == "nodes_1000000":
            engine_limit_combo.setCurrentText("Позиции 1000000" if self.language == "bg" else "Nodes 1000000")
        layout.addRow("Сила на двигателя:" if self.language == "bg" else "Engine Strength:", engine_limit_combo)
        
        time_spin = QSpinBox()
        time_spin.setRange(1, 180)
        time_spin.setValue(self.time_control // 60)
        layout.addRow("Време (мин):" if self.language == "bg" else "Time (min):", time_spin)
        
        inc_spin = QSpinBox()
        inc_spin.setRange(0, 60)
        inc_spin.setValue(self.increment)
        layout.addRow("Инкремент (сек):" if self.language == "bg" else "Increment (sec):", inc_spin)
        
        pv_moves_spin = QSpinBox()
        pv_moves_spin.setRange(5, 50)
        pv_moves_spin.setValue(self.pv_moves_display)
        layout.addRow("Брой ходове в PV:" if self.language == "bg" else "Moves in PV line:", pv_moves_spin)
        
        theme_combo = QComboBox()
        theme_combo.addItems(["Тъмно синя" if self.language == "bg" else "Dark Blue", 
                            "Класическа" if self.language == "bg" else "Classic", 
                            "Зелена" if self.language == "bg" else "Green", 
                            "Синя" if self.language == "bg" else "Blue", 
                            "Лилава" if self.language == "bg" else "Purple", 
                            "Сива" if self.language == "bg" else "Gray"])
        theme_map = {
            "dark_blue": "Тъмно синя" if self.language == "bg" else "Dark Blue",
            "classic": "Класическа" if self.language == "bg" else "Classic",
            "green": "Зелена" if self.language == "bg" else "Green",
            "blue": "Синя" if self.language == "bg" else "Blue",
            "purple": "Лилава" if self.language == "bg" else "Purple",
            "gray": "Сива" if self.language == "bg" else "Gray"
        }
        theme_combo.setCurrentText(theme_map.get(self.current_theme, "Тъмно синя" if self.language == "bg" else "Dark Blue"))
        layout.addRow("Тема на дъската:" if self.language == "bg" else "Board Theme:", theme_combo)
        
        language_combo = QComboBox()
        language_combo.addItems(["Български", "English"])
        language_combo.setCurrentText("Български" if self.language == "bg" else "English")
        layout.addRow("Език:" if self.language == "bg" else "Language:", language_combo)

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(dlg.accept)
        btns.rejected.connect(dlg.reject)
        layout.addRow(btns)
        
        if dlg.exec_() == QDialog.Accepted:
            old_mode = self.is_engine_vs_engine
            old_color = self.player_color
            
            self.is_engine_vs_engine = (mode_combo.currentText() in ["Двигател срещу двигател", "Engine vs Engine"])
            
            color_text = color_combo.currentText()
            if color_text in ["Случайно", "Random"]:
                self.player_color = random.choice([chess.WHITE, chess.BLACK])
            elif color_text in ["Бели", "White"]:
                self.player_color = chess.WHITE
            else:
                self.player_color = chess.BLACK
                
            self.time_control = time_spin.value() * 60
            self.increment = inc_spin.value()
            self.pv_moves_display = pv_moves_spin.value()
            
            theme_text = theme_combo.currentText()
            theme_map_reverse = {
                "Тъмно синя": "dark_blue", "Dark Blue": "dark_blue",
                "Класическа": "classic", "Classic": "classic",
                "Зелена": "green", "Green": "green",
                "Синя": "blue", "Blue": "blue",
                "Лилава": "purple", "Purple": "purple",
                "Сива": "gray", "Gray": "gray"
            }
            self.current_theme = theme_map_reverse.get(theme_text, "dark_blue")
            self.set_theme_colors()
            
            lang_text = language_combo.currentText()
            self.language = "bg" if lang_text == "Български" else "en"
            
            self.settings.set("game_mode", "engine_vs_engine" if self.is_engine_vs_engine else "human_vs_engine")
            self.settings.set("player_color", "white" if self.player_color == chess.WHITE else "black")
            self.settings.set("time_control", self.time_control)
            self.settings.set("increment", self.increment)
            self.settings.set("pv_moves_display", self.pv_moves_display)
            self.settings.set("theme", self.current_theme)
            self.settings.set("language", self.language)
            
            limit_text = engine_limit_combo.currentText()
            if "Дълбочина 15" in limit_text or "Depth 15" in limit_text:
                self.engine_strength = "depth_15"
            elif "Дълбочина 20" in limit_text or "Depth 20" in limit_text:
                self.engine_strength = "depth_20"
            elif "Дълбочина 10" in limit_text or "Depth 10" in limit_text:
                self.engine_strength = "depth_10"
            elif "Позиции" in limit_text or "Nodes" in limit_text:
                self.engine_strength = "nodes_1000000"
            elif "Въз основа на време" in limit_text or "Time based" in limit_text:
                self.engine_strength = "time_based"
            
            self.settings.set("engine_strength", self.engine_strength)
            
            if old_mode != self.is_engine_vs_engine or old_color != self.player_color:
                self.new_game()
            else:
                QMessageBox.information(self, "Настройки" if self.language == "bg" else "Settings", 
                                      "Настройките са приложени." if self.language == "bg" else "Settings applied.")
            
            self.apply_theme()
            self.board_w.update()
            self.apply_menu_styles(self.menuBar())
            
            self.highlights_widget.update_highlights(self.current_board)
            self.update_turn_display()

    def new_game(self):
        self.timer.stop()
        self.stop_engine_thread()
        self.stop_analysis()
        
        self.is_paused = False
        self.btn_pause.setText("Пауза" if self.language == "bg" else "Pause")
        
        self.close_engines()
        
        engine1_path = self.settings.get("engine1_path", "")
        if engine1_path and os.path.exists(engine1_path) and HAS_ENGINE:
            try:
                self.engine = chess.engine.SimpleEngine.popen_uci(engine1_path)
                self.engine.configure({"Threads": self.eng1_threads})
            except:
                self.engine = None
                
        engine2_path = self.settings.get("engine2_path", "")
        if engine2_path and os.path.exists(engine2_path) and HAS_ENGINE:
            try:
                self.engine2 = chess.engine.SimpleEngine.popen_uci(engine2_path)
                self.engine2.configure({"Threads": self.eng2_threads})
            except:
                self.engine2 = None
        
        self.game_board.reset()
        self.current_board = self.game_board
        self.is_navigating_history = False
        self.book_move_played = False
        
        self.move_evaluations = {}
        self.current_move_number = 0
        
        self.white_clock.reset(self.time_control)
        self.black_clock.reset(self.time_control)
        
        self.move_table.clearContents()
        self.move_table.setRowCount(0)
        
        self.game_chart.clear_chart()
        
        self.board_w.last_move = None
        self.board_w.selected = None
        self.board_w.legal_moves_for_selected = []
        self.board_w.best_engine_move = None
        self.eval_bar.set_score(0)
        self.board_w.update()
        self.fen_label.setText(self.current_board.fen())

        self.update_book_info()
        self.highlights_widget.update_highlights(self.current_board)
        self.update_turn_display()

        self.timer.start(1000)

        if self.is_engine_vs_engine:
            self.human_turn = False
            self.start_analysis()
            if self.game_board.turn == chess.WHITE and self.engine:
                QTimer.singleShot(500, self.start_engine)
            elif self.game_board.turn == chess.BLACK and self.engine2:
                QTimer.singleShot(500, self.start_engine)
        else:
            current_turn = self.game_board.turn
            self.human_turn = (current_turn == self.player_color)
            
            if not self.human_turn and self.engine:
                self.start_analysis()
                QTimer.singleShot(500, self.start_engine)
            elif self.human_turn and self.engine:
                self.start_analysis()

    def start_analysis(self):
        if not HAS_ENGINE:
            return
            
        current_engine = None
        if self.is_engine_vs_engine:
            if self.current_board.turn == chess.WHITE:
                current_engine = self.engine
            else:
                current_engine = self.engine2
        else:
            current_engine = self.engine
        
        if not current_engine:
            return
            
        if self.analysis_thread and self.analysis_thread.isRunning():
            self.analysis_thread.stop()
            self.analysis_thread.wait(2000)
            self.analysis_thread = None
        
        self.analysis_thread = EngineThread(
            current_engine, 
            self.current_board, 
            time_control=0,
            is_analysis=True
        )
        self.analysis_thread.info.connect(self.update_analysis)
        self.analysis_thread.error.connect(self.handle_engine_error)
        self.analysis_thread.start()

    def stop_analysis(self):
        if self.analysis_thread and self.analysis_thread.isRunning():
            self.analysis_thread.stop()
            self.analysis_thread.wait(2000)
            self.analysis_thread = None
            
        self.board_w.best_engine_move = None
        self.board_w.update()

    def stop_engine_thread(self):
        if self.game_thread and self.game_thread.isRunning():
            self.game_thread.stop()
            self.game_thread.wait(2000)
            self.game_thread = None
                
        self.engine_thinking = False
        self.book_move_played = False

    def handle_engine_error(self, error_msg):
        self.restart_engine()

    def restart_engine(self):
        engine1_path = self.settings.get("engine1_path", "")
        if engine1_path and os.path.exists(engine1_path) and HAS_ENGINE:
            try:
                self.close_engines()
                self.engine = chess.engine.SimpleEngine.popen_uci(engine1_path)
                self.engine.configure({"Threads": self.eng1_threads})
            except:
                self.engine = None
        
        engine2_path = self.settings.get("engine2_path", "")
        if engine2_path and os.path.exists(engine2_path) and HAS_ENGINE:
            try:
                self.close_engines()
                self.engine2 = chess.engine.SimpleEngine.popen_uci(engine2_path)
                self.engine2.configure({"Threads": self.eng2_threads})
            except:
                self.engine2 = None

    def history_clicked(self, item):
        row = item.row()
        
        column = item.column()
        
        moves_to_restore = 0
        if column == 1:
            moves_to_restore = row * 2
        elif column == 2:
            moves_to_restore = row * 2 + 1
        
        self.game_board.reset()
        
        for i in range(min(moves_to_restore, len(self.game_board.move_stack))):
            move = self.game_board.move_stack[i]
            self.game_board.push(move)
        
        self.current_board = self.game_board
        self.is_navigating_history = True
        
        self.board_w.last_move = None
        if self.current_board.move_stack:
            self.board_w.last_move = self.current_board.move_stack[-1]
        self.board_w.update()
        self.update_book_info()
        self.fen_label.setText(self.current_board.fen())
        self.highlights_widget.update_highlights(self.current_board)
        self.update_turn_display()
        
        if self.analysis_thread:
            self.stop_analysis()
        QTimer.singleShot(100, self.start_analysis)

    def copy_fen(self):
        cb = QApplication.clipboard()
        cb.setText(self.current_board.fen())
        QMessageBox.information(self, "FEN", "FEN нотацията е копирана в клипборда!" if self.language == "bg" else "Current board FEN copied to clipboard!")

    def paste_fen(self):
        text, ok = QInputDialog.getText(self, "Постави FEN" if self.language == "bg" else "Paste FEN", 
                                       "Въведете FEN нотация:" if self.language == "bg" else "Enter FEN string:")
        if ok and text:
            try:
                self.game_board.set_fen(text)
                self.current_board = self.game_board
                
                # КОРЕКЦИЯ: Актуализиране на състоянието на играта
                self.stop_engine_thread()
                self.is_engine_vs_engine = False
                self.player_color = self.game_board.turn
                self.human_turn = True  # ВАЖНО: Разрешаваме ход на човека веднага
                
                self.game_chart.clear_chart()
                # ВАЖНА КОРЕКЦИЯ: Нулиране на селекцията на дъската
                self.board_w.selected = None
                self.board_w.legal_moves_for_selected = []
                
                self.update_turn_display()
                
                # ВАЖНА КОРЕКЦИЯ: Проверка за пешки, които са на място за промоция
                # и автоматична промоция до царица, ако е необходимо
                for square in chess.SQUARES:
                    piece = self.game_board.piece_at(square)
                    if piece and piece.piece_type == chess.PAWN:
                        rank = chess.square_rank(square)
                        # Ако пешка е на последния ред за нейния цвят
                        if (piece.color == chess.WHITE and rank == 7) or (piece.color == chess.BLACK and rank == 0):
                            self.game_board.set_piece_at(square, chess.Piece(chess.QUEEN, piece.color))
                
                self.board_w.update()
                self.update_book_info()
                self.fen_label.setText(self.game_board.fen())
                self.highlights_widget.update_highlights(self.game_board)
                
                if self.engine:
                    self.start_analysis()
                
            except Exception as e:
                QMessageBox.warning(self, "Грешка" if self.language == "bg" else "Error", 
                                  f"Невалиден FEN: {e}" if self.language == "bg" else f"Invalid FEN: {e}")

    def save_pgn(self):
        """Запазва текущата игра като PGN файл"""
        path, _ = QFileDialog.getSaveFileName(self, "Запази PGN" if self.language == "bg" else "Save PGN", 
                                            f"game_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pgn", 
                                            "PGN файлове (*.pgn)" if self.language == "bg" else "PGN Files (*.pgn)")
        if path:
            try:
                game = chess.pgn.Game()
                game.setup(self.game_board)
                node = game
                for move in self.game_board.move_stack:
                    node = node.add_main_variation(move)
                
                with open(path, "w", encoding="utf-8") as f:
                    f.write(str(game))
                
                QMessageBox.information(self, "PGN", "Играта е запазена успешно!" if self.language == "bg" else "Game saved successfully!")
            except Exception as e:
                QMessageBox.warning(self, "Грешка" if self.language == "bg" else "Error", 
                                  f"Грешка при запазване: {str(e)}" if self.language == "bg" else f"Error saving: {str(e)}")

    def save_pgn_database(self):
        """Запазва всички партии от PGN базата данни"""
        if not self.pgn_games:
            QMessageBox.warning(self, "Грешка" if self.language == "bg" else "Error",
                              "Няма партии за запазване!" if self.language == "bg" else "No games to save!")
            return
            
        path, _ = QFileDialog.getSaveFileName(self, "Запази PGN база" if self.language == "bg" else "Save PGN Database", 
                                            f"games_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pgn", 
                                            "PGN файлове (*.pgn)" if self.language == "bg" else "PGN Files (*.pgn)")
        if path:
            try:
                with open(path, "w", encoding="utf-8") as f:
                    for game in self.pgn_games:
                        f.write(str(game))
                        f.write("\n\n")
                
                QMessageBox.information(self, "PGN", "PGN базата е запазена успешно!" if self.language == "bg" else "PGN database saved successfully!")
            except Exception as e:
                QMessageBox.warning(self, "Грешка" if self.language == "bg" else "Error", 
                                  f"Грешка при запазване: {str(e)}" if self.language == "bg" else f"Error saving: {str(e)}")

    def load_pgn(self):
        """Зарежда PGN файл (единична партия)"""
        path, _ = QFileDialog.getOpenFileName(self, "Зареди PGN" if self.language == "bg" else "Load PGN", "", 
                                            "PGN файлове (*.pgn)" if self.language == "bg" else "PGN Files (*.pgn)")
        if path:
            self.load_pgn_file(path)

    def load_pgn_file(self, path):
        """Зарежда PGN файл с прогрес диалог"""
        # Създаваме диалог за прогрес
        progress_dialog = ProgressDialog(self, "Зареждане на PGN файл..." if self.language == "bg" else "Loading PGN file...")
        progress_dialog.show()
        
        # Създаваме тред за зареждане
        self.pgn_loader_thread = PGNLoaderThread(path)
        self.pgn_loader_thread.progress.connect(lambda value: progress_dialog.set_progress(value))
        self.pgn_loader_thread.games_loaded.connect(lambda games: self.on_pgn_games_loaded(games, path, progress_dialog))
        self.pgn_loader_thread.error.connect(lambda err: self.on_pgn_load_error(err, progress_dialog))
        self.pgn_loader_thread.start()

    def on_pgn_games_loaded(self, games, path, progress_dialog):
        """Обработка на заредените игри"""
        progress_dialog.close()
        
        if not games:
            QMessageBox.warning(self, "Грешка" if self.language == "bg" else "Error",
                              "Няма партии във файла." if self.language == "bg" else "No games found in file.")
            return
        
        self.pgn_file_path = path
        self.pgn_games = games
        self.current_pgn_index = 0
        
        if len(self.pgn_games) == 1:
            # Ако има само една партия, зареждаме я директно
            self.load_pgn_game(0)
            QMessageBox.information(self, "PGN", "Партията е заредена успешно!" if self.language == "bg" else "Game loaded successfully!")
        else:
            # Ако има повече партии, показваме диалог за избор
            self.show_pgn_database_dialog()
    
    def on_pgn_load_error(self, error_msg, progress_dialog):
        """Обработка на грешка при зареждане"""
        progress_dialog.close()
        QMessageBox.warning(self, "Грешка" if self.language == "bg" else "Error", 
                          f"Грешка при зареждане на PGN: {error_msg}" if self.language == "bg" else f"Error loading PGN: {error_msg}")

    def load_pgn_database(self):
        """Отваря PGN база данни"""
        self.load_pgn()

    def show_pgn_database_dialog(self):
        """Показва диалогов прозорец за избор на партия от PGN база"""
        if not self.pgn_games:
            return
        
        # Ако вече има отворен PGN диалог, показваме го отново
        if self.pgn_dialog:
            self.pgn_dialog.show()
            self.pgn_dialog.raise_()
            self.pgn_dialog.activateWindow()
            return
        
        # Създаваме нов диалог
        self.pgn_dialog = PGNGameDialog(self, self.pgn_games)
        self.pgn_dialog.load_game.connect(self.on_pgn_game_selected)
        self.pgn_dialog.finished.connect(lambda: setattr(self, 'pgn_dialog', None))
        self.pgn_dialog.show()
    
    def on_pgn_game_selected(self, index):
        """Зарежда избраната партия от диалога"""
        self.current_pgn_index = index
        self.load_pgn_game(self.current_pgn_index)
        
        # Показваме съобщение, но не затваряме диалога
        if self.language == "bg":
            QMessageBox.information(self, "PGN", f"Партия {index + 1} заредена успешно!")
        else:
            QMessageBox.information(self, "PGN", f"Game {index + 1} loaded successfully!")

    def load_pgn_game(self, index):
        """Зарежда конкретна партия от PGN базата"""
        if index < 0 or index >= len(self.pgn_games):
            return
        
        game = self.pgn_games[index]
        
        # Ресетваме текущата игра
        self.game_board = game.board()
        for move in game.mainline_moves():
            self.game_board.push(move)
        
        self.current_board = self.game_board
        self.refresh_move_list()
        self.board_w.update()
        self.update_book_info()
        self.book_move_played = False
        self.fen_label.setText(self.current_board.fen())
        self.highlights_widget.update_highlights(self.current_board)
        self.update_turn_display()
        
        self.move_evaluations = {}
        self.current_move_number = len(self.game_board.move_stack)
        
        # Изчистваме и реинициализираме графиката с оценките
        self.game_chart.clear_chart()
        
        # Генерираме оценки за всички ходове
        temp_board = chess.Board()
        # Ако играта не започва от начална позиция
        if self.game_board.move_stack:
            try:
                temp_board.set_fen(self.game_board.move_stack[0].board().fen())
            except:
                pass
        
        move_count = 0
        for i, move in enumerate(self.game_board.move_stack):
            move_count += 1
            san_move = temp_board.san(move)
            
            # Тук може да добавите логика за изчисляване на оценка за всеки ход
            # За сега ще използваме случайни оценки за демонстрация
            import random
            eval_cp = random.randint(-300, 300)
            
            # Актуализираме графиката
            self.game_chart.update_chart(move_count, san_move, eval_cp)
            temp_board.push(move)
        
        if self.analysis_thread:
            self.stop_analysis()
        
        QTimer.singleShot(100, self.start_analysis)
        
        # Актуализираме информацията за PGN
        self.update_pgn_info()
        
        # Обновяваме оценката
        self.eval_bar.set_score(0)
        self.last_eval = 0

    def get_pgn_game_info(self, game):
        """Връща информация за PGN партията"""
        if self.language == "bg":
            info = "Информация за партията:\n"
            info += "══════════════════════════════\n\n"
            
            headers = [
                ("Събитие", "Event"),
                ("Бели", "White"),
                ("Черни", "Black"),
                ("Резултат", "Result"),
                ("Дата", "Date"),
                ("Място", "Site"),
                ("Кръг", "Round"),
                ("Отваряне", "Opening"),
                ("ECO", "ECO")
            ]
        else:
            info = "Game information:\n"
            info += "══════════════════════════════\n\n"
            
            headers = [
                ("Event", "Event"),
                ("White", "White"),
                ("Black", "Black"),
                ("Result", "Result"),
                ("Date", "Date"),
                ("Site", "Site"),
                ("Round", "Round"),
                ("Opening", "Opening"),
                ("ECO", "ECO")
            ]
        
        for display_name, header_name in headers:
            value = game.headers.get(header_name, "")
            if value:
                info += f"{display_name}: {value}\n"
        
        # Брой ходове
        moves_count = len(list(game.mainline_moves()))
        if self.language == "bg":
            info += f"\nБрой ходове: {moves_count}\n"
        else:
            info += f"\nNumber of moves: {moves_count}\n"
        
        return info

    def next_pgn_game(self):
        """Зарежда следващата партия в PGN базата"""
        if self.pgn_games and self.current_pgn_index < len(self.pgn_games) - 1:
            self.current_pgn_index += 1
            self.load_pgn_game(self.current_pgn_index)
        else:
            if self.language == "bg":
                QMessageBox.information(self, "PGN", "Това е последната партия в базата.")
            else:
                QMessageBox.information(self, "PGN", "This is the last game in the database.")

    def prev_pgn_game(self):
        """Зарежда предишната партия в PGN базата"""
        if self.pgn_games and self.current_pgn_index > 0:
            self.current_pgn_index -= 1
            self.load_pgn_game(self.current_pgn_index)
        else:
            if self.language == "bg":
                QMessageBox.information(self, "PGN", "Това е първата партия в базата.")
            else:
                QMessageBox.information(self, "PGN", "This is the first game in the database.")

    def human_move(self, move):
        """ВАЖНА КОРЕКЦИЯ: Обработка на ход от човека - поправена логика за промоция"""
        if self.is_engine_vs_engine:
            return

        if not self.engine:
            QMessageBox.warning(self, "Грешка" if self.language == "bg" else "Error", 
                      "Първо заредете двигател!" if self.language == "bg" else "Load engine first!")
            return
    
        # Проверка дали е ред на човека
        if self.game_board.turn != self.player_color:
            QMessageBox.warning(self, "Не е ваш ред" if self.language == "bg" else "Not your turn", 
                      f"Ред е на {'белите' if self.game_board.turn == chess.WHITE else 'черните'}!" if self.language == "bg" else f"It's {'white' if self.game_board.turn == chess.WHITE else 'black'}'s turn!")
            return
    
        if self.engine_thinking:
            self.stop_engine_thread()
            self.engine_thinking = False
    
        if self.is_navigating_history:
            moves_in_current = len(self.current_board.move_stack)
            temp_stack = list(self.game_board.move_stack)[:moves_in_current]
            self.game_board.reset()
            for m in temp_stack:
                self.game_board.push(m)
            self.is_navigating_history = False
    
        # ВАЖНА КОРЕКЦИЯ: Проверка за промоция
        p = self.game_board.piece_at(move.from_square)
        if p and p.piece_type == chess.PAWN:
            target_rank = chess.square_rank(move.to_square)
            is_promotion = (p.color == chess.WHITE and target_rank == 7) or (p.color == chess.BLACK and target_rank == 0)
            
            if is_promotion and not move.promotion:
                # Ако пешката се движи до последния ред, но няма указана промоция
                # Трябва да отворим диалог за промоция
                dlg = PromotionDialog(p.color, self.language, self)
                if dlg.exec_():
                    move.promotion = dlg.result
                else:
                    # Потребителят отказа, не правим ход
                    return

        # ВАЖНА ПРОВЕРКА: Уверяваме се, че ходът е легален
        if move not in self.game_board.legal_moves:
            QMessageBox.warning(self, "Невалиден ход" if self.language == "bg" else "Invalid Move", 
                      "Ходът не е легален!" if self.language == "bg" else "Move is not legal!")
            return
        
        # ЗАПАЗВАНЕ НА НОТАЦИЯТА ПРЕДИ ДА ИЗПЪЛНИМ ХОДА
        move_notation = self.game_board.san(move)
        
        self.game_board.push(move)

        self.current_board = self.game_board

        prev_color = not self.game_board.turn
        if self.increment > 0:
            if prev_color == chess.WHITE: 
                self.white_clock.add_increment(self.increment)
            else: 
                self.black_clock.add_increment(self.increment)

        self.refresh_move_list()
        self.board_w.last_move = move
        self.board_w.selected = None
        self.board_w.legal_moves_for_selected = []
        self.board_w.update()
        self.fen_label.setText(self.current_board.fen())
        self.highlights_widget.update_highlights(self.current_board)
        self.update_turn_display()

        self.play_sound("move")

        self.current_move_number += 1
        if self.last_eval is not None:
            # Оценката в self.last_eval вече е от перспективата на белите (коригирано в update_analysis)
            eval_for_chart = self.last_eval
            
            # ИЗПОЛЗВАНЕ НА ЗАПАЗЕНАТА НОТАЦИЯ
            self.game_chart.update_chart(self.current_move_number, move_notation, eval_for_chart)

        self.human_turn = False
        self.book_move_played = False

        if self.game_board.is_game_over():
            self.game_over()
        else:
            if self.analysis_thread:
                self.stop_analysis()
            QTimer.singleShot(100, self.start_analysis)
            QTimer.singleShot(200, self.start_engine)

    def refresh_move_list(self):
        """Опреснява таблицата с ходовете"""
        self.move_table.clearContents()
        self.move_table.setRowCount(0)
        
        temp_board = chess.Board()
        # Ако играта не започва от начална позиция (напр. след FEN импорт)
        if self.game_board.move_stack:
            # Опитваме се да намерим началната позиция
            try:
                temp_board.set_fen(self.game_board.move_stack[0].board().fen())
            except:
                # Ако не можем, приемаме стандартна или текущата без ходове
                pass

        row = 0
        i = 0
        
        while i < len(self.game_board.move_stack):
            try:
                move_num = row + 1
                
                self.move_table.insertRow(row)
                
                item_num = QTableWidgetItem(str(move_num))
                item_num.setTextAlignment(Qt.AlignCenter)
                self.move_table.setItem(row, 0, item_num)
                
                move_white = self.game_board.move_stack[i]
                san_white = temp_board.san(move_white)
                item_white = QTableWidgetItem(san_white)
                item_white.setTextAlignment(Qt.AlignCenter)
                if self.dark_theme_enabled:
                    item_white.setForeground(QColor(255, 255, 255))
                else:
                    item_white.setForeground(QColor(0, 0, 0))
                self.move_table.setItem(row, 1, item_white)
                temp_board.push(move_white)
                i += 1
                
                if i < len(self.game_board.move_stack):
                    move_black = self.game_board.move_stack[i]
                    san_black = temp_board.san(move_black)
                    item_black = QTableWidgetItem(san_black)
                    item_black.setTextAlignment(Qt.AlignCenter)
                    if self.dark_theme_enabled:
                        item_black.setForeground(QColor(255, 255, 255))
                    else:
                        item_black.setForeground(QColor(0, 0, 0))
                    self.move_table.setItem(row, 2, item_black)
                    temp_board.push(move_black)
                    i += 1
                else:
                    item_black = QTableWidgetItem("")
                    item_black.setTextAlignment(Qt.AlignCenter)
                    self.move_table.setItem(row, 2, item_black)
                
                row += 1
            except Exception as e:
                # Ако има грешка при генериране на SAN (напр. нелегален ход в историята)
                # просто прескачаме или добавяме суров ход
                print(f"Error in refresh_move_list: {e}")
                break
        
        self.move_table.resizeColumnsToContents()
        header = self.move_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        
        for r in range(self.move_table.rowCount()):
            self.move_table.setRowHeight(r, 30)
        
        if self.move_table.rowCount() > 0:
            self.move_table.scrollToBottom()

    def get_book_move(self):
        if not self.book:
            return None
            
        current_move_num = (len(self.game_board.move_stack) // 2) + 1
        
        if current_move_num > self.book_max_depth:
            return None
            
        try:
            entries = list(self.book.find_all(self.game_board))
            if not entries:
                return None
                
            entries = list(entries)
            entries.sort(key=lambda x: x.weight, reverse=True)
            
            best_entry = entries[0]
            if best_entry.move in self.game_board.legal_moves:
                return best_entry.move
            else:
                return None
                
        except Exception:
            return None

    def start_engine(self):
        if self.human_turn or self.is_paused:
            return
            
        if self.engine_thinking:
            return
        
        if self.game_board.is_game_over():
            self.game_over()
            return
        
        self.update_book_info()
        self.update_turn_display()

        if not HAS_ENGINE:
            return

        current_move_num = (len(self.game_board.move_stack) // 2) + 1
        if current_move_num <= self.book_max_depth:
            book_move = self.get_book_move()
            if book_move:
                QTimer.singleShot(50, lambda: self.engine_move(book_move))
                return

        current_engine = None

        if self.is_engine_vs_engine:
            if self.game_board.turn == chess.WHITE:
                current_engine = self.engine
            else:
                current_engine = self.engine2
            
            if not current_engine:
                QMessageBox.warning(self, "Грешка в двигателя" if self.language == "bg" else "Engine Error", 
                                   f"Няма зареден двигател за {'белите' if self.game_board.turn == chess.WHITE else 'черните'}" if self.language == "bg" else f"No engine loaded for {'White' if self.game_board.turn == chess.WHITE else 'Black'}")
                return
        else:
            if not self.engine: 
                QMessageBox.warning(self, "Грешка в двигателя" if self.language == "bg" else "Engine Error", 
                                   "Няма зареден двигател!" if self.language == "bg" else "No engine loaded!")
                return
            current_engine = self.engine

        self.engine_thinking = True
        
        if self.analysis_thread:
            self.stop_analysis()
        
        if self.game_board.turn == chess.WHITE:
            remaining_time = self.white_clock.time
        else:
            remaining_time = self.black_clock.time
        
        if self.engine_strength == "time_based":
            pass
        elif self.engine_strength == "depth_15":
            remaining_time = 0
        elif self.engine_strength == "depth_20":
            remaining_time = 0
        elif self.engine_strength == "depth_10":
            remaining_time = 0
        elif self.engine_strength == "nodes_1000000":
            remaining_time = 0
        
        self.game_thread = EngineThread(
            current_engine, 
            self.game_board, 
            time_control=remaining_time,
            increment=self.increment
        )
        self.game_thread.info.connect(self.update_analysis)
        self.game_thread.bestmove.connect(self.engine_move)
        self.game_thread.error.connect(self.handle_engine_error)
        self.game_thread.start()

    def engine_move(self, move):
        if not move:
            self.engine_thinking = False
            return
        
        self.engine_thinking = False
        
        try:
            if move not in self.game_board.legal_moves:
                if not self.game_board.is_game_over():
                    QTimer.singleShot(100, self.start_engine)
                return
        
            # ЗАПАЗВАНЕ НА НОТАЦИЯТА ПРЕДИ ДА ИЗПЪЛНИМ ХОДА
            san_move = self.game_board.san(move)
            
            self.game_board.push(move)
            
            self.current_board = self.game_board
            
            prev_color = not self.game_board.turn
            if self.increment > 0:
                if prev_color == chess.WHITE: 
                    self.white_clock.add_increment(self.increment)
                else: 
                    self.black_clock.add_increment(self.increment)
                
            self.refresh_move_list()
            
            self.board_w.last_move = move
            self.board_w.update()
            self.fen_label.setText(self.current_board.fen())
            self.highlights_widget.update_highlights(self.current_board)
            self.update_turn_display()
            
            self.play_sound("move")
            
            self.current_move_number += 1
            if self.last_eval is not None:
                # Оценката в self.last_eval вече е от перспективата на белите
                eval_for_chart = self.last_eval
                
                # ИЗПОЛЗВАНЕ НА ЗАПАЗЕНАТА НОТАЦИЯ
                self.game_chart.update_chart(self.current_move_number, san_move, eval_for_chart)

            if self.game_board.is_game_over():
                self.game_over()
            else:
                if self.is_engine_vs_engine:
                    self.human_turn = False
                    self.book_move_played = False
                    QTimer.singleShot(100, self.start_analysis)
                    QTimer.singleShot(200, self.start_engine)
                else:
                    self.human_turn = (self.game_board.turn == self.player_color)
                    self.book_move_played = False
                    
                    QTimer.singleShot(100, self.start_analysis)
                    
                    if not self.human_turn:
                        QTimer.singleShot(200, self.start_engine)
        except Exception as e:
            self.engine_thinking = False
            if self.game_board.is_game_over():
                self.game_over()
            else:
                QTimer.singleShot(200, self.start_engine)

    def game_over(self):
        self.timer.stop()
        self.stop_engine_thread()
        self.stop_analysis()
        
        if self.game_board.is_checkmate():
            winner = "Белите" if self.game_board.turn == chess.BLACK and self.language == "bg" else "White" if self.game_board.turn == chess.BLACK else "Черните" if self.language == "bg" else "Black"
            self.play_sound("notify")
            QMessageBox.information(self, "Край на играта" if self.language == "bg" else "Game Over", 
                                  f"Шах и мат! {winner} печелят!" if self.language == "bg" else f"Checkmate! {winner} wins!")
        elif self.game_board.is_stalemate():
            self.play_sound("notify")
            QMessageBox.information(self, "Край на играта" if self.language == "bg" else "Game Over", 
                                  "Пат! Равенство!" if self.language == "bg" else "Stalemate! Draw!")
        elif self.game_board.is_insufficient_material():
            QMessageBox.information(self, "Край на играта" if self.language == "bg" else "Game Over", 
                                  "Равенство - недостатъчен материал!" if self.language == "bg" else "Draw - insufficient material!")
        elif self.game_board.is_seventyfive_moves():
            QMessageBox.information(self, "Край на играта" if self.language == "bg" else "Game Over", 
                                  "Равенство - правило за 75 хода!" if self.language == "bg" else "Draw - 75 moves rule!")
        elif self.game_board.is_fivefold_repetition():
            QMessageBox.information(self, "Край на играта" if self.language == "bg" else "Game Over", 
                                  "Равенство - петкратно повторение!" if self.language == "bg" else "Draw - fivefold repetition!")
        elif self.game_board.can_claim_fifty_moves():
            QMessageBox.information(self, "Край на играта" if self.language == "bg" else "Game Over", 
                                  "Равенство - може да се заяви правило за 50 хода!" if self.language == "bg" else "Draw - 50-move rule can be claimed!")
        elif self.game_board.can_claim_threefold_repetition():
            QMessageBox.information(self, "Край на играта" if self.language == "bg" else "Game Over", 
                                  "Равенство - може да се заяви троен повтор!" if self.language == "bg" else "Draw - threefold repetition can be claimed!")
        elif self.game_board.is_variant_draw():
            QMessageBox.information(self, "Край на играта" if self.language == "bg" else "Game Over", 
                                  "Равенство по вариант!" if self.language == "bg" else "Variant draw!")
        else:
            QMessageBox.information(self, "Край на играта" if self.language == "bg" else "Game Over", 
                                  "Играта завърши!" if self.language == "bg" else "Game finished!")

    def offer_draw(self):
        if self.game_board.is_game_over():
            return
            
        if self.is_engine_vs_engine:
            QMessageBox.warning(self, "Предложение за реми" if self.language == "bg" else "Draw Offer",
                              "В режим двигател срещу двигател не може да се предлага реми." if self.language == "bg" else "Cannot offer draw in engine vs engine mode.")
            return
        
        reply = QMessageBox.question(
            self, 
            "Предложение за реми" if self.language == "bg" else "Draw Offer",
            "Желаете ли да предложите реми на противника?" if self.language == "bg" else "Do you want to offer a draw to your opponent?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            if self.game_board.can_claim_draw():
                QMessageBox.information(self, "Реми" if self.language == "bg" else "Draw",
                                      "Играта е реми според правилата!" if self.language == "bg" else "The game is a draw by rules!")
                self.game_over()
                return
            
            if not self.human_turn and self.engine:
                engine_response = random.choice([True, False])
                
                if engine_response:
                    QMessageBox.information(self, "Предложение за реми" if self.language == "bg" else "Draw Offer",
                                          "Двигателят приема реми! Играта свършва." if self.language == "bg" else "The engine accepts the draw! Game ends.")
                    self.game_board.set_fen(self.game_board.fen())
                    self.game_over()
                else:
                    QMessageBox.information(self, "Предложение за реми" if self.language == "bg" else "Draw Offer",
                                          "Двигателят отказва реми. Играта продължава." if self.language == "bg" else "The engine declines the draw. Game continues.")
            else:
                QMessageBox.information(self, "Предложение за реми" if self.language == "bg" else "Draw Offer",
                                      "Предложението е изпратено. Изчакайте отговор на противника." if self.language == "bg" else "Draw offer sent. Waiting for opponent response.")

    def update_analysis(self, info):
        # Оптимизация: Обновяваме само при значими промени (напр. дълбочина или нов PV)
        if "depth" in info: 
            self.depth_label.setText(f"{'Дълбочина' if self.language == 'bg' else 'Depth'}: {info['depth']}")
        
        if "nodes" in info:
            n = info['nodes']
            if n > 1000000: 
                self.nodes_label.setText(f"{'Позиции' if self.language == 'bg' else 'Nodes'}: {n/1000000:.1f}M")
            elif n > 1000: 
                self.nodes_label.setText(f"{'Позиции' if self.language == 'bg' else 'Nodes'}: {n/1000:.1f}K")
            else: 
                self.nodes_label.setText(f"{'Позиции' if self.language == 'bg' else 'Nodes'}: {n}")

        if "score" in info:
            sc = info["score"]
            # Оценката трябва да бъде ВИНАГИ от перспективата на БЕЛИТЕ в интерфейса
            # sc е PovScore. sc.white() връща Score спрямо белите.
            
            white_score = sc.white()
            if white_score.is_mate():
                mate_in = white_score.mate() # Положително за мат от белите, отрицателно за черните
                self.eval_label.setText(f"{'Мат след' if self.language == 'bg' else 'Mate in'} {mate_in}")
                s = 1000 if mate_in > 0 else -1000
                self.eval_bar.set_score(s)
                self.last_eval = s
            else:
                s = white_score.score()
                if s is not None:
                    # Положителна оценка (+) означава предимство за белите
                    # Отрицателна оценка (-) означава предимство за черните
                    eval_text = f"{s/100:+.2f}"
                    self.eval_label.setText(f"{'Оценка' if self.language == 'bg' else 'Eval'}: {eval_text}")
                    self.eval_bar.set_score(s)
                    self.last_eval = s

        # ВАЖНО: Веднаша обновяваме PV линията (Principal Variation) за реално време
        if "pv" in info and len(info["pv"]) > 0:
            pv_moves = info["pv"][:self.pv_moves_display]
            current_move_number = len(self.current_board.move_stack) // 2 + 1
            
            move_list = []
            temp_board = self.current_board.copy()
            
            for move in pv_moves:
                if move not in temp_board.legal_moves:
                    break
                try:
                    san_move = temp_board.san(move)
                    move_list.append(san_move)
                    temp_board.push(move)
                except Exception:
                    break
            
            if move_list:
                formatted_moves = []
                move_num = current_move_number
                
                # Коректно номериране при ход на черните
                if self.current_board.turn == chess.BLACK:
                    formatted_moves.append(f"<span style='color: #cccccc'>{move_num}... {move_list[0]}</span>")
                    move_list = move_list[1:]
                    move_num += 1
                
                i = 0
                while i < len(move_list):
                    white_move = move_list[i] if i < len(move_list) else ""
                    black_move = move_list[i+1] if i+1 < len(move_list) else ""
                    
                    if white_move and black_move:
                        formatted_moves.append(f"<span style='color: #ffffff'>{move_num}. {white_move:10s}</span> <span style='color: #cccccc'>{black_move}</span>")
                    elif white_move:
                        formatted_moves.append(f"<span style='color: #ffffff'>{move_num}. {white_move}</span>")
                    
                    move_num += 1
                    i += 2
                
                pv_text = "<div style='font-family: Consolas; font-size: 11pt; line-height: 1.5;'>" + " ".join(formatted_moves) + "</div>"
                self.pv_text.setHtml(pv_text)
                
                # Показване на стрелка за най-добрия ход в реално време
                if pv_moves and pv_moves[0] in self.current_board.legal_moves:
                    self.board_w.best_engine_move = pv_moves[0]
                    self.board_w.update()

    def tick_clock(self):
        if self.game_board.is_game_over() or self.is_paused:
            return
            
        turn = self.game_board.turn
        if turn == chess.WHITE:
            self.white_clock.tick(self.white_clock.time < 30)
        else:
            self.black_clock.tick(self.black_clock.time < 30)

    def toggle_pause(self):
        if self.is_paused:
            self.is_paused = False
            self.btn_pause.setText("Пауза" if self.language == "bg" else "Pause")
            self.timer.start(1000)
            
            if not self.human_turn and not self.is_engine_vs_engine and self.engine and not self.engine_thinking:
                QTimer.singleShot(500, self.start_engine)
            elif self.is_engine_vs_engine and not self.engine_thinking:
                QTimer.singleShot(500, self.start_engine)
        else:
            self.is_paused = True
            self.btn_pause.setText("Продължи" if self.language == "bg" else "Resume")
            self.timer.stop()
            if self.engine_thinking:
                self.stop_engine_thread()

    def undo_move(self):
        if len(self.game_board.move_stack) > 0:
            self.game_board.pop()
            self.current_board = self.game_board
            self.refresh_move_list()
            self.board_w.last_move = None if len(self.game_board.move_stack) == 0 else self.game_board.move_stack[-1]
            self.board_w.update()
            self.fen_label.setText(self.current_board.fen())
            self.highlights_widget.update_highlights(self.current_board)
            self.update_turn_display()
            self.book_move_played = False
            
            if self.analysis_thread:
                self.stop_analysis()
            QTimer.singleShot(100, self.start_analysis)
            
            self.current_move_number = max(0, self.current_move_number - 1)
            if self.current_move_number > 0 and self.current_move_number <= len(self.game_chart.eval_history):
                # Актуализираме графиката след отмяна
                self.game_chart.eval_history = self.game_chart.eval_history[:self.current_move_number]
                self.game_chart.move_history = self.game_chart.move_history[:self.current_move_number]
                self.game_chart.update()

    def redo_move(self):
        # Note: This would require storing undone moves, which we don't currently do.
        # For now, just show a message.
        QMessageBox.information(self, "Повторение" if self.language == "bg" else "Redo", 
                              "Функцията за повторение на ход все още не е имплементирана." if self.language == "bg" else "Redo move functionality not yet implemented.")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = App()
    window.show()
    sys.exit(app.exec_())
    
