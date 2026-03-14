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

import os
import random
import re
import string

import clang.cindex
from clang.cindex import CursorKind

clang.cindex.Config.set_library_file(
    "C:/Program Files/LLVM/bin/libclang.dll"
)

errors = [
    {'type': 'no error', 'message': 'it`s work ok', 'error_num': 0},
    {'type': 'error', 'message': 'file wasn`t read', 'error_num': 1},
    {'type': 'error', 'message': 'file wasn`t write', 'error_num': 2},
    {'type': 'error', 'message': 'comments weren`t delete', 'error_num': 3},
    {'type': 'error', 'message': 'free space wasn`t delete', 'error_num': 4},
    {'type': 'error', 'message': 'name wasn`t generate', 'error_num': 5},
    {'type': 'error', 'message': 'code name identeficators weren`t rename',
     'error_num': 6},
    {'type': 'error', 'message': 'no one function wasn`t overload',
     'error_num': 7}
]

# CONST
PUNCT = string.punctuation
ALPHABET = string.ascii_letters
INCLUDE_PATTERN = (
    r'#(?:include\s*[<"][^>"]+[>"]|'
    r'define\s+[A-Za-z_][A-Za-z0-9_]*(?:\s+.*)?)'
)
STRING_PATTERN = r'"([^"\\]|\\.)*"'

operation_res = [i for i in range(7)]  # ошибки, которые произошли во время
# вполнения кода
protected_includes = []  # директивы препроцессора, которые заменены на
# защищенные поля
protected_strings = []  # строки, которые заменены на защищенные поля
reserved_names = []  # имена, которые нельзя использовать для замены
name_mapping = {}  # старое название: новое название
func_args = {}  # количество аргументов: массив имен функций

def _protect_includes(match):
    protected_includes.append(match.group())
    return f'__PROTECTED_INCLUDE_{len(protected_includes) - 1}__'

def _protect_strings(match):
    protected_strings.append(match.group())
    return f'__PROTECTED_STRING_{len(protected_strings) - 1}__'

def _restore_elements(code):
    # Приводим директивы препроцессора к первоначальному виду
    for i, strng in enumerate(protected_strings):
        code = code.replace(f'__PROTECTED_STRING_{i}__', strng)

    # Приводим строки к первоначальному виду
    for i, include in enumerate(protected_includes):
        code = code.replace(f'__PROTECTED_INCLUDE_{i}__', include)

    return code

def _clear_variables():
    global operation_res, protected_includes, protected_strings
    global reserved_names, name_mapping, func_args

    operation_res = [i for i in range(7)]
    protected_includes = []
    protected_strings = []
    reserved_names = []
    name_mapping = {}
    func_args = {}

def _to_process_errors(operation_res):
    all_ok = True

    # Проверяем есть ли ошибки
    for error in operation_res:
        if error == errors[0]:
            print('✅', error)
        else:
            all_ok = False
            print('❌', error)

    if all_ok == False:
        print("==========Something went wrong===========")
    else:
        print("==============Everything OK==============")

def _get_declarations_from_node(
        node, file_name: str, func_args: dict, func_args_temp: dict
) -> tuple:
    """
    Рекурсивно собирает все объявления из узла AST
    Args:
        node: узел AST
        file_name (str): имя файла для проверки принадлежности
        func_args (dict): глобальный словарь функций по количеству аргументов
        func_args_temp (dict): временный словарь функций по количеству аргументов
    Returns:
        tuple: (variables, functions, classes) из текущего узла и его потомков
    """
    variables = set()
    functions = list()
    classes = set()

    # Проверяем текущий узел
    if node.kind in [
        CursorKind.VAR_DECL, CursorKind.PARM_DECL, CursorKind.FIELD_DECL
    ]:
        if node.spelling and node.spelling:
            # Проверяем, что узел из нашего файла
            if (node.location.file and
                    os.path.abspath(node.location.file.name) ==
                    os.path.abspath(file_name)):
                variables.add(node.spelling)

    elif node.kind in [CursorKind.CLASS_DECL, CursorKind.STRUCT_DECL]:
        if node.spelling and not node.spelling.startswith('__'):
            classes.add(node.spelling)

    elif node.kind in [
        CursorKind.FUNCTION_DECL, CursorKind.CXX_METHOD,
        CursorKind.CONSTRUCTOR, CursorKind.DESTRUCTOR
    ]:
        if node.spelling and node.spelling:
            # Проверяем, что узел из нашего файла
            if (node.location.file and
                    os.path.abspath(node.location.file.name) ==
                    os.path.abspath(file_name)):
                # Исключаем специальные функции
                if (not node.spelling.startswith('__') and
                        all(node.spelling != 'operator' + i
                            for i in PUNCT)):
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
                    if node.spelling not in [
                        f for funcs in func_args.values() for f in funcs
                    ]:
                        # Добавляем как временную запись
                        if param_count not in func_args_temp:
                            func_args_temp[param_count] = []
                        func_args_temp[param_count].append(node.spelling)
                    # ======================================

    # Рекурсивно обходим дочерние узлы
    for child in node.get_children():
        child_vars, child_funcs, child_classes = _get_declarations_from_node(
            child, file_name, func_args, func_args_temp
        )
        variables.update(child_vars)
        functions.extend(child_funcs)
        classes.update(child_classes)

    return variables, functions, classes

def _parse_ast(file_name: str) -> tuple:
    """
    Парсит C++ файл и собирает все объявления из AST
    Args:
        file_name (str): Путь к файлу для парсинга
    Returns:
        tuple: (all_vars, all_funcs, all_classes, func_args_temp)
    """

    index = clang.cindex.Index.create()
    translation_unit = index.parse(file_name, args=['-std=c++17'])
    func_args_temp = {}

    all_vars, all_funcs, all_classes = _get_declarations_from_node(
        translation_unit.cursor, file_name, func_args, func_args_temp
    )

    return all_vars, all_funcs, all_classes, func_args_temp

def _filter_variables(all_vars: set, code: str) -> set:
    """
    Фильтрует переменные по их фактическому использованию в коде
    Args:
        all_vars (set): Множество всех переменных из AST
        code (str): Исходный код для проверки использования
    Returns:
        set: Отфильтрованные имена переменных
    """
    final_vars = set()

    for var in all_vars:
        if re.search(r'\b' + re.escape(var) + r'\b', code):
            final_vars.add(var)

    return final_vars

def _filter_functions(
        all_funcs: list, func_args_temp: dict, code: str
) -> list:
    """
    Фильтрует функции по их фактическому использованию в коде
    и обновляет func_args
    Args:
        all_funcs (list): Список всех функций из AST
        func_args_temp (dict): Временный словарь функций по количеству аргументов
        code (str): Исходный код для проверки использования
    Returns:
        list: Отфильтрованные имена функций
    """

    final_funcs = list()

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

    return final_funcs

def _filter_classes(all_classes: set, final_funcs: list) -> set:
    """
    Фильтрует классы, определяя какие из них используются как конструкторы
    Args:
        all_classes (set): Множество всех классов из AST
        final_funcs (list): Отфильтрованные функции
    Returns:
        set: Отфильтрованные имена классов
    """
    final_classes = set()

    for clas in all_classes:
        for func in final_funcs:
            if func == clas:
                final_classes.add(clas)

    return final_classes

def _add_to_reserved(
        final_vars: set, final_funcs: list, final_classes: set
) -> None:
    """
    Добавляет отфильтрованные идентификаторы в список зарезервированных имен
    Args:
        final_vars (set): Отфильтрованные переменные
        final_funcs (list): Отфильтрованные функции
        final_classes (set): Отфильтрованные классы
    """
    for i in final_vars:
        reserved_names.append(i)
    for i in final_funcs:
        reserved_names.append(i)
    for i in final_classes:
        reserved_names.append(i)

def _extract_identifiers(file_name: str, code: str) -> tuple:
    """
    Собирает информацию о переменных, функциях и классах в полученном C++ коде
    Args:
        file_name (str): имя файла
        code (str): C++ код
    Returns:
        tuple: (final_vars, final_funcs, final_classes)
               - final_vars: имена переменных, используемых в C++ коде
               - final_funcs: имена функций, используемых в C++ коде
               - final_classes: имена классов, используемых в C++ коде
    """
    # Шаг 1: Парсим AST и получаем все объявления
    all_vars, all_funcs, all_classes, func_args_temp = _parse_ast(file_name)

    # Шаг 2: Фильтруем переменные
    final_vars = _filter_variables(all_vars, code)

    # Шаг 3: Фильтруем функции
    final_funcs = _filter_functions(all_funcs, func_args_temp, code)

    # Шаг 4: Фильтруем классы
    final_classes = _filter_classes(all_classes, final_funcs)

    # Шаг 5: Добавляем в зарезервированные
    _add_to_reserved(final_vars, final_funcs, final_classes)

    # Шаг 6: Возвращаем отсортированные результаты
    return (
        sorted(final_vars, key=len, reverse=True),
        sorted(final_funcs, key=len, reverse=True),
        sorted(final_classes, key=len, reverse=True)
    )

def read_file(file_name: str) -> tuple:
    """
    Читает файл
    Args:
        file_name (имя файла)
    Return:
        content (содержимое файла),
        errors[0]
    or
        '',
        errors[1]
    """
    try:
        with open(file_name, "r", encoding='UTF-8-sig') as file:
            # пробуем прочитать в utf-8
            content = file.read()
            return content, errors[0]
    except Exception:
        try:
            with open(file_name, "r", encoding='cp1251') as file:
                # пробуем прочитать в cp1251
                content = file.read()
                return content, errors[0]
        except Exception:
            # если ничего не получилось возвращаем ошибку чтения
            return '', errors[1]

def write_file(file_name: str, content: str) -> dict:
    """
    Записывает строку в файл
    Args:
        file_name (имя файла),
        content (строка для записи)
    Return:
        errors[0]
    or
        errors[2]
    """
    try:
        with open(file_name, "w", encoding='UTF-8') as file:
            # пробуем записать в utf-8
            file.write(content)
            return errors[0]

    except Exception:
        try:
            with open(file_name, "w", encoding='cp1251') as file:
                # пробуем записать в cp1251
                file.write(content)
                return errors[0]

        except Exception:
            # если ничего не получилось возвращаем ошибку записи
            return errors[2]

def del_comments(code: str) -> tuple:
    """
    Удаляет коментарии из кода, написанного на C++
    Args:
        code (C++ код)
    Return:
        no_comments_code (C++ код без коментариев),
        errors[0]
    or
        code,
        errors[3]
    """
    no_comments_code = ''
    try:
        # Удаляем многострочные комментарии
        tmp_code = re.sub(r'/\*.*?\*/', '', code, flags=re.DOTALL)
        tmp_code = tmp_code.split('\n')

        # Удаляем однострочные комментарии
        for line in tmp_code:
            result_line = ''

            for i in range(0, len(line)):
                if line[i:i + 2] == '//':
                    break
                else:
                    result_line += line[i]

            no_comments_code += result_line + '\n'

        return no_comments_code, errors[0]

    except Exception:
        return code, errors[3]

def del_free_space(code: str) -> tuple:
    """
    Удаляет пробельные символы в начале и конце строк и переводы строк.
    Директивы препроцессора остаются каждый на своей строке
    Args:
        code (C++ код)
    Return:
        no_free_space_code (C++ код без пробельных символов в начале и конце
        строк и без переводов строки),
        errors[0]
    or
        code,
        errors[4]
    """
    no_free_space_code = ''
    tmp_code = code.split("\n")

    try:
        # Удаляем незначащие пробельные символы
        for line in tmp_code:
            # с концов строки удаляем пробельные символы
            line = line.strip()

            # если директива препроцессора, в начале и в конце добавляем '\n'
            if "__PROTECTED_INCLUDE_" in line:
                no_free_space_code = (
                        no_free_space_code + '\n' + line + '\n'
                )
                continue
            else:
                # Для обычного кода добавляем пробел, если нужно
                if (no_free_space_code and
                        not no_free_space_code[-1].isspace() and line):
                    # Проверяем, добавить ли пробел между ключевыми словами
                    last_char = (
                        no_free_space_code[-1] if no_free_space_code else ''
                    )
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
    Генерирует название, состоящие из латинских букв в верхнем и нижнем
    регистрах заданной длины
    Args:
        length (длина генерируемого названия)
    Return:
        new_name (сгенерированное название),
        errors[0]
    or
        '',
        errors[5]
    """
    new_name = ""
    try:
        while new_name in reserved_names or new_name == "":
            new_name = ''.join(
                random.choice(ALPHABET) for i in range(length)
            )

        reserved_names.append(new_name)
        return new_name, errors[0]

    except Exception:
        return '', errors[5]

def rename_ids(code: str, identifiers: list, length: int = 40) -> tuple:
    """
    Переименовывает идентификаторы на сгенерированные имена заданной длины
    Args:
        code (C++ код),
        identifiers (спиок имен идентификаторов, которые будут переименнованы),
        length (длина генерируемого названия)
    Return:
        renamed_idents_code (код с новыми именами идентификаторов из списка),
        errors[0]
    or
        code,
        errors[6]
    """
    tmp_code = code

    try:
        # Заменяем идентификаторы
        for old_name in identifiers:
            if old_name not in name_mapping:  # непонятки
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
    Берет как основную функцию первую функцию из полученного списка и заменяет
    остальные функции на основную
    Args:
        code (C++ код),
        func_list (список функций, которые будут перегружены)
    Return:
        overloaded_func_code (код с перегруженными функциями из списка)
    or
        code
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
    Учитывает, что названия функций, которые должны совпадать с названиями
    классов и уже перегруженные функции не будут перегружены.
    Перегружаются только функции с разным количеством принимаемых аргументов.
    Args:
        code (C++ код),
        functions_to_skip (функций, которые нельзя перегружать)
    Return:
        overloaded_func_code (C++ код с перегруженными функциями),
        errors[0]
    or
        code,
        errors[7]
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
                        break  # Выходим из while, переходим к следующему
                        # arg_count

                # Если после while список пуст, помечаем это количество
                # аргументов как пропущенное
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
    Удаляет комментарии и пустое пространство из C++ кода, перегружает функции
    и заменяет имена переменных и функций на произвольные
    Args:
        file_name (имя файла из которого будет прочитан код),
        file_name (имя файла в который будет записан результат)
    Return:
        obf_code (обфусцированный C++ код)
    """
    # Сбрасываем глобальные переменные
    _clear_variables()
    # Читаем файл
    code, operation_res[0] = read_file(file_name)
    # Получаем списки переменных, функций и функций, которые нельзя перегружать
    all_variables, all_functions, functions_to_skip = _extract_identifiers(
        file_name, code
    )

    # Заполняем массив функций, которые нельзя перегружать
    for i in all_functions:
        if all_functions.count(i) != 1:
            functions_to_skip.append(i)

    # Защищаем строковые литералы и директивы препроцессора
    obf_code = re.sub(INCLUDE_PATTERN, _protect_includes, code)
    obf_code = re.sub(STRING_PATTERN, _protect_strings, obf_code)
    print(protected_includes)
    # Удаляем комментарии
    obf_code, operation_res[1] = del_comments(obf_code)
    # Перегружаем функции
    obf_code, operation_res[2] = func_overloading(obf_code, functions_to_skip)
    # Переименовываем переменные
    obf_code, operation_res[3] = rename_ids(obf_code, all_variables)
    # Переименовываем функции
    obf_code, operation_res[4] = rename_ids(obf_code, all_functions)
    # Удаляем пустое пространство
    obf_code, operation_res[5] = del_free_space(obf_code)
    # Восстанавливаем директивы препроцессора и строковые литералы
    obf_code = _restore_elements(obf_code)
    # Записываем результат в файл
    operation_res[6] = write_file(new_file_name, obf_code)
    _to_process_errors(operation_res)

    return obf_code
