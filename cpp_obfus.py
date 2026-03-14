# cpp_obfus - инструмент для обфускации C++ кода
# Copyright (C) 2026 Баранов Даниил Васильевич
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

'''
=============================HOW TO USE===============================

import cpp_obfus

obfuscate(file_name) # reads file_name and writes obfuscated code in 'obfuscated.cpp'

or

obfuscate(file_name, new_file_name) # reads file_name and writes obfuscated code in new_file_name
======================================================================
'''



import string
import clang.cindex
from clang.cindex import CursorKind
import random
import os
import re
clang.cindex.Config.set_library_file("C:/Program Files/LLVM/bin/libclang.dll")

errors = [
    {'type': 'no error', 'message': 'it`s work ok', 'error_num': 0},
    {'type': 'error', 'message': 'file wasn`t read', 'error_num': 1},
    {'type': 'error', 'message': 'file wasn`t write', 'error_num': 2},
    {'type': 'error', 'message': 'comments weren`t delete', 'error_num': 3},
    {'type': 'error', 'message': 'free space wasn`t delete', 'error_num': 4},
    {'type': 'error', 'message': 'name wasn`t generate', 'error_num': 5},
    {'type': 'error', 'message': 'code name identeficators weren`t rename', 'error_num': 6},
    {'type': 'error', 'message': 'no one function wasn`t overload', 'error_num': 7}
]

# CONST
PUNCT = string.punctuation
ALPHABET = string.ascii_letters
INCLUDE_PATTERN = r'#(?:include\s*[<"][^>"]+[>"]|define\s+[A-Za-z_][A-Za-z0-9_]*(?:\s+.*)?)'
STRING_PATTERN = r'"([^"\\]|\\.)*"'

what_went_wrong = [i for i in range(7)] # ошибки которые произошли во время вполнения кода
protected_includes = [] # директивы препроцессора, которые заменены на защищенные поля
protected_strings = [] # строки, которые заменены на защищенные поля
reserved_names = [] # имена, которые нельзя использовать для замены
name_mapping = {} # старое название: новое название
func_args = {} # количество аргументов: массив имен функций

def _check(error: dict):
    if error!=errors[0]:
        print(error)

def _protect_includes(match):
    protected_includes.append(match.group())
    return f'__PROTECTED_INCLUDE_{len(protected_includes) - 1}__'

def _protect_strings(match):
    protected_strings.append(match.group())
    return f'__PROTECTED_STRING_{len(protected_strings) - 1}__'

def _restore_elements(code):
    # Приводим директивы препроцессора и строки к первоначальному виду
    for i, strng in enumerate(protected_strings):
        code = code.replace(f'__PROTECTED_STRING_{i}__', strng)
    for i, include in enumerate(protected_includes):
        code = code.replace(f'__PROTECTED_INCLUDE_{i}__', include)
    return code

def _clear_variables():
    global what_went_wrong, protected_includes, protected_strings, reserved_names, name_mapping, func_args
    what_went_wrong = [i for i in range(7)]
    protected_includes = []  # директивы препроцессора, которые заменены на защищенные поля
    protected_strings = []  # строки, которые заменены на защищенные поля
    reserved_names = []  # имена, которые нельзя использовать для замены
    name_mapping = {}  # старое название: новое название
    func_args = {}  # количество аргументов: массив имен функций

def _to_process_errors(what_went_wrong):
    all_ok = True
    for error in what_went_wrong:
        if error == errors[0]:
            print('✅', error)
        else:
            all_ok = False
            print('❌', error)
    if all_ok == False:
        print("==========Something went wrong==========")
    else:
        print("==============Everything OK==============")

def read_file(file_name: str) -> tuple:
    """
    Читает файл
    args: file_name (имя файла)
    return: content (содержимое файла), errors[0]/'', errors[1]
    """
    try:
        with open(file_name, "r", encoding='UTF-8-sig') as file: # пробуем прочитать в utf-8
            content = file.read()
            return content, errors[0]
    except Exception:
        try:
            with open(file_name, "r", encoding='cp1251') as file: # если не получилось прочитать в utf-8 читаем в cp1251
                content = file.read()
                return content, errors[0]
        except Exception:
            return '', errors[1] # если ничего не получилось возвращаем ошибку чтения

def write_file(file_name: str, content: str) -> dict:
    """
    Записывает строку в файл
    args: file_name (имя файла), content (строка для записи)
    return: errors[0]/errors[2]
    """
    try:
        with open(file_name, "w", encoding='UTF-8') as file: # пробуем записать в utf-8
            file.write(content)
            return errors[0]
    except Exception:
        try:
            with open(file_name, "w", encoding='cp1251') as file: # если не получилось записать в utf-8 записываем в cp1251
                file.write(content)
                return errors[0]
        except Exception:
            return errors[2] # если ничего не получилось возвращаем ошибку записи

def del_comments(code: str) -> tuple:
    """
    Удаляет коментарии из кода, написанного на C++
    args: code (C++ код)
    return: no_comments_code (C++ код без коментариев), errors[0]/code, errors[3]
    """
    no_comments_code = ''
    try:
        tmp_code = re.sub(r'/\*.*?\*/', '', code, flags=re.DOTALL) # Удаляем многострочные комментарии

        # Удаляем однострочные комментарии, но не в строках
        tmp_code = tmp_code.split('\n')
        for line in tmp_code:
            result_line = ''
            for i in range(0, len(line)):
                if line[i:i + 2] == '//':
                    break
                else:
                    result_line += line[i]
            no_comments_code+=result_line+'\n'
        return no_comments_code, errors[0]
    except Exception:
        return code, errors[3]

def del_free_space(code: str) -> tuple:
    """
    Удаляет пробельные символы в начале и конце строк и переводы строк.
    Директивы препроцессора остаются каждый на своей строке
    args: code (C++ код)
    return: no_free_space_code (C++ код без пробельных символов в начале и конце строк и без переводов строки), errors[0]/code, errors[4]
    """
    no_free_space_code = ''
    try:
        tmp_code = code.split("\n")
        for line in tmp_code:
            line = line.strip() # с концов строки удаляем пробельные символы
            if "__PROTECTED_INCLUDE_" in line: # если директива препроцессора, в начале и в конце добавляем перевод строки
                no_free_space_code = no_free_space_code + '\n' + line + '\n'
                continue
            else:
                # Для обычного кода добавляем пробел, если нужно
                if no_free_space_code and not no_free_space_code[-1].isspace() and line:
                    # Проверяем, нужно ли добавить пробел между ключевыми словами
                    last_char = no_free_space_code[-1] if no_free_space_code else ''
                    first_char = line[0] if line else ''

                    # Добавляем пробел между else и return, if и ( и т.д.
                    if (last_char.isalpha() and first_char.isalpha()) or \
                            (last_char.isalpha() and first_char == '(') or \
                            (last_char == ')' and first_char.isalpha()) or \
                            (last_char.isdigit() and first_char.isalpha()):
                        no_free_space_code += ' '

                no_free_space_code += line
        return no_free_space_code, errors[0]
    except Exception:
        return code, errors[4]

def generate_new_name(length: int) -> tuple:
    """
    Генерирует название, состоящие из латинских букв в верхнем и нижнем регистрах заданной длины
    args: length (длина генерируемого названия)
    return: new_name (сгенерированное название), errors[0]/'', errors[5]
    """
    new_name = ""
    try:
        while new_name in reserved_names or new_name == "":
            new_name = ''.join(random.choice(ALPHABET) for i in range(length))
        reserved_names.append(new_name)
        return new_name, errors[0]
    except Exception:
        return '', errors[5]

# черный ящик
def _get_cpp_names(file_name: str, code: str) -> tuple:
    """
    Собирает информацию о переменных, функциях и классах в полученном C++ коде
    args: file_name (имя файла), code (C++ код)
    return: final_vars (имена переменных, используемых в C++ коде), final_funcs (имена функций, используемых в C++ коде), final_classes (имена классов, используемых в C++ коде)
    """
    # Парсим файл
    index = clang.cindex.Index.create()
    translation_unit = index.parse(file_name, args=['-std=c++17'])
    # Временный словарь для сбора информации до фильтрации
    func_args_temp = {}
    def get_declarations(node):
        """Рекурсивно собирает все объявления переменных и функций"""
        variables = set()
        functions = list()
        classes = set()

        # Проверяем текущий узел
        if node.kind in [CursorKind.VAR_DECL, CursorKind.PARM_DECL, CursorKind.FIELD_DECL]:
            if node.spelling and node.spelling:
                # Проверяем, что узел из нашего файла
                if node.location.file and os.path.abspath(node.location.file.name) == os.path.abspath(file_name):
                    variables.add(node.spelling)

        elif node.kind in [CursorKind.CLASS_DECL, CursorKind.STRUCT_DECL]:
            if node.spelling and not node.spelling.startswith('__'):
                classes.add(node.spelling)

        elif node.kind in [CursorKind.FUNCTION_DECL, CursorKind.CXX_METHOD,
                           CursorKind.CONSTRUCTOR, CursorKind.DESTRUCTOR]:
            if node.spelling and node.spelling:
                # Проверяем, что узел из нашего файла
                if node.location.file and os.path.abspath(node.location.file.name) == os.path.abspath(file_name):
                    # Исключаем специальные функции
                    if not node.spelling.startswith('__') and all(node.spelling != 'operator'+i for i in PUNCT):
                        functions.append(node.spelling)

                        # ========== ПОДСЧЕТ АРГУМЕНТОВ ==========
                        # Считаем количество параметров функции
                        param_count = 0
                        for child in node.get_children():
                            if child.kind == CursorKind.PARM_DECL:
                                param_count += 1

                        # Сохраняем в словарь (предварительно, до фильтрации)
                        if param_count not in func_args:
                            func_args[param_count] = []

                        # Добавляем функцию во временный словарь
                        # (потом отфильтруем)
                        if node.spelling not in [f for funcs in func_args.values() for f in funcs]:
                            # Добавляем как временную запись
                            if param_count not in func_args_temp:
                                func_args_temp[param_count] = []
                            func_args_temp[param_count].append(node.spelling)
                        # ======================================

        # Рекурсивно обходим дочерние узлы
        for child in node.get_children():
            child_vars, child_funcs, child_classes = get_declarations(child)
            variables.update(child_vars)
            functions.extend(child_funcs)
            classes.update(child_classes)

        return variables, functions, classes



    # Получаем все объявления
    all_vars, all_funcs, all_classes = get_declarations(translation_unit.cursor)

    final_vars = set()
    final_funcs = list()
    final_classes = set()

    for var in all_vars:
        # Ищем имя как отдельное слово (не часть другого слова)
        if re.search(r'\b' + re.escape(var) + r'\b', code):
            final_vars.add(var)

    # Фильтруем функции и заполняем итоговый словарь
    for func in all_funcs:
        # Ищем имя функции (с возможными скобками после)
        if 'main' == func:
            continue
        if re.search(r'\b' + re.escape(func) + r'\s*\(', code):
            final_funcs.append(func)

            # Ищем эту функцию во временном словаре
            for count, funcs_list in func_args_temp.items():
                if func in funcs_list:
                    if count not in func_args:
                        func_args[count] = []
                    func_args[count].append(func)
                    break
    for clas in all_classes:
        for func in final_funcs:
            if func == clas:
                final_classes.add(clas)

    # Добавляем имена в зарезервированные
    for i in final_vars:
        reserved_names.append(i)
    for i in final_funcs:
        reserved_names.append(i)
    for i in final_classes:
        reserved_names.append(i)

    return sorted(final_vars, key=len, reverse=True), sorted(final_funcs, key=len, reverse=True), sorted(final_classes, key=len, reverse=True)

def rename_identifiers(code: str, identifiers: list, length: int = 40) -> tuple:
    """
    Переименовывает идентификаторы на сгенерированные имена заданной длины
    args: code (C++ код), identifiers (спиок имен идентификаторов, которые будут переименнованы), length (длина генерируемого названия)
    return: renamed_idents_code (код с переименнованными идентификаторами из списка имен), errors[0]/code, errors[6]
    """
    tmp_code = code
    try:
        # Заменяем идентификаторы
        for old_name in identifiers:
            if old_name not in name_mapping: # непонятки
                name_mapping[old_name], error = generate_new_name(length)
                if error != errors[0]:
                    name_mapping[old_name] = old_name
            new_name = name_mapping[old_name]

            # Заменяем с учетом границ слова
            pattern = r'\b' + re.escape(old_name) + r'\b'
            tmp_code = re.sub(pattern, new_name, tmp_code)

        renamed_idents_code = tmp_code
        return renamed_idents_code, errors[0]

    except Exception:
        return code, errors[6]

def overloading(code: str, func_list: list) -> str:
    """
    Берет как основную функцию первую функцию из полученного списка и заменяет остальные функции на основную
    args: code (C++ код), func_list (список функций, которые будут перегружены)
    return: overloaded_func_code (код с перегруженными функциями из списка)/code
    """
    tmp_code = code
    try:
        target_name = func_list[0]
        for func in func_list[1:]:
            # Заменяем с учетом границ слова и последующей скобки
            pattern = r'\b' + re.escape(func) + r'\s*\('
            replacement = target_name + '('
            tmp_code = re.sub(pattern, replacement, tmp_code)
        overloaded_func_code = tmp_code
        return overloaded_func_code
    except Exception:
        return code

def func_overloading(code: str, functions_to_skip: list) -> tuple:
    """
    Составляет список функций, которые будут перегружены и перегружает.
    Учитывает, что названия функций, которые должны совпадать с названиями классов и уже перегруженные функции не будут перегружены.
    Перегружаются только функции с разным количеством принимаемых аргументов.
    args: code (C++ код), functions_to_skip (функций, которые нельзя перегружать)
    return: overloaded_func_code (C++ код с максимальным количеством перегруженных функций), errors[0]/code, errors[7]
    """
    skip_counts = []
    tmp_code = code
    try:
        while True:
            to_overload = []

            # Проходим по всем количествам аргументов
            for arg_count in sorted(func_args.keys()):
                if arg_count in skip_counts:
                    continue

                # Пока есть функции в списке для этого количества аргументов
                while func_args[arg_count]:
                    current_func = func_args[arg_count][0]

                    # Проверяем, нужно ли пропустить
                    if current_func in functions_to_skip:
                        # Пропускаем и удаляем
                        func_args[arg_count].pop(0)
                        # Продолжаем цикл while для проверки следующей функции
                    else:
                        # Нашли подходящую функцию
                        to_overload.append(current_func)
                        func_args[arg_count].pop(0)
                        break  # Выходим из while, переходим к следующему arg_count

                # Если после while список пуст, помечаем это количество аргументов как пропущенное
                if not func_args[arg_count]:
                    skip_counts.append(arg_count)

            # Проверяем, сколько функций набрали
            if len(to_overload) < 2:
                break

            # Перегружаем
            tmp_code = overloading(tmp_code, to_overload)
        overloaded_func_code = tmp_code
        return overloaded_func_code, errors[0]

    except Exception:
        return code, errors[7]

# главная функция
def obfuscate(file_name: str, new_file_name: str = 'obfuscated.cpp') -> str:
    """
    Удаляет комментарии и пустое пространство из C++ кода, перегружает функции и заменяет имена переменных и функций на произвольные
    args: file_name (имя файла из которого будет прочитан код), file_name (имя файла в который будет записан результат)
    return: obf_code (обфусцированный C++ код)
    """
    # Сбрасываем глобальные переменные
    _clear_variables()
    # Читаем файл
    code, what_went_wrong[0] = read_file(file_name)
    # Получаем списки переменных, функций и функций, которые нельзя перегружать
    all_variables, all_functions, functions_to_skip = _get_cpp_names(file_name, code)
    # Заполняем массив функций, которые нельзя перегружать
    for i in all_functions:
        if all_functions.count(i) != 1:
            functions_to_skip.append(i)
    # Защищаем строковые литералы и директивы препроцессора
    obf_code = re.sub(INCLUDE_PATTERN, _protect_includes, code)
    obf_code = re.sub(STRING_PATTERN, _protect_strings, obf_code)
    print(protected_includes)
    # Удаляем комментарии
    obf_code, what_went_wrong[1] = del_comments(obf_code)
    # Перегружаем функции
    obf_code, what_went_wrong[2] = func_overloading(obf_code, functions_to_skip)
    # Переименовываем переменные
    obf_code, what_went_wrong[3] = rename_identifiers(obf_code, all_variables)
    # Переименовываем функции
    obf_code, what_went_wrong[4] = rename_identifiers(obf_code, all_functions)
    # Удаляем пустое пространство
    obf_code, what_went_wrong[5] = del_free_space(obf_code)
    # Восстанавливаем директивы препроцессора и строковые литералы
    obf_code = _restore_elements(obf_code)
    # Записываем результат в файл
    what_went_wrong[6] = write_file(new_file_name, obf_code)
    _to_process_errors(what_went_wrong)
    return obf_code
