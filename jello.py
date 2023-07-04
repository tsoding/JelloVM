#!/usr/bin/env python3

"JVM in Python"

import pprint
import sys
import io
from typing import Any, cast

pp = pprint.PrettyPrinter()

CONSTANT_Class              = 7
CONSTANT_Fieldref           = 9
CONSTANT_Methodref          = 10
CONSTANT_InterfaceMethodref = 11
CONSTANT_String             = 8
CONSTANT_Integer            = 3
CONSTANT_Float              = 4
CONSTANT_Long               = 5
CONSTANT_Double             = 6
CONSTANT_NameAndType        = 12
CONSTANT_Utf8               = 1
CONSTANT_MethodHandle       = 15
CONSTANT_MethodType         = 16
CONSTANT_InvokeDynamic      = 18

class_access_flags = [
    ("ACC_PUBLIC"     , 0x0001),
    ("ACC_FINAL"      , 0x0010),
    ("ACC_SUPER"      , 0x0020),
    ("ACC_INTERFACE"  , 0x0200),
    ("ACC_ABSTRACT"   , 0x0400),
    ("ACC_SYNTHETIC"  , 0x1000),
    ("ACC_ANNOTATION" , 0x2000),
    ("ACC_ENUM"       , 0x4000)
]

method_access_flags = [
    ("ACC_PUBLIC"       , 0x0001),
    ("ACC_PRIVATE"      , 0x0002),
    ("ACC_PROTECTED"    , 0x0004),
    ("ACC_STATIC"       , 0x0008),
    ("ACC_FINAL"        , 0x0010),
    ("ACC_SYNCHRONIZED" , 0x0020),
    ("ACC_BRIDGE"       , 0x0040),
    ("ACC_VARARGS"      , 0x0080),
    ("ACC_NATIVE"       , 0x0100),
    ("ACC_ABSTRACT"     , 0x0400),
    ("ACC_STRICT"       , 0x0800),
    ("ACC_SYNTHETIC"    , 0x1000),
]

def parse_flags(value: int, flags: list[tuple[str, int]]) -> list[str]:
    "Parse flags from value and return names of flags set"
    return [name for (name, mask) in flags if (value&mask) != 0]

def parse_u1(f: io.IOBase) -> int: return int.from_bytes(f.read(1), 'big')
def parse_u2(f: io.IOBase) -> int: return int.from_bytes(f.read(2), 'big')
def parse_u4(f: io.IOBase) -> int: return int.from_bytes(f.read(4), 'big')

def parse_attributes(f: io.BufferedReader, count: int) -> list[dict[str, int | bytes]]:
    "Parse attributes from file"
    attributes = []
    for _ in range(count):
        # attribute_info {
        #     u2 attribute_name_index;
        #     u4 attribute_length;
        #     u1 info[attribute_length];
        # }
        attribute: dict[str, int | bytes] = {}
        attribute['attribute_name_index'] = parse_u2(f)
        attribute_length = parse_u4(f)
        attribute['info'] = f.read(attribute_length)
        attributes.append(attribute)
    return attributes

def parse_class_file(file_path: str) -> dict[str, Any]:
    "Parse class file given it's path"
    with open(file_path, "rb") as f:
        clazz: dict[str, Any] = {}
        clazz['magic'] = hex(parse_u4(f))
        clazz['minor'] = parse_u2(f)
        clazz['major'] = parse_u2(f)
        constant_pool_count = parse_u2(f)
        constant_pool = []
        for _ in range(constant_pool_count-1):
            cp_info: dict[str, int | str | bytes] = {}
            tag = parse_u1(f)
            if tag == CONSTANT_Methodref:
                cp_info['tag'] = 'CONSTANT_Methodref'
                cp_info['class_index'] = parse_u2(f)
                cp_info['name_and_type_index'] = parse_u2(f)
            elif tag == CONSTANT_Class:
                cp_info['tag'] = 'CONSTANT_Class'
                cp_info['name_index'] = parse_u2(f)
            elif tag == CONSTANT_NameAndType:
                cp_info['tag'] = 'CONSTANT_NameAndType'
                cp_info['name_index'] = parse_u2(f)
                cp_info['descriptor_index'] = parse_u2(f)
            elif tag == CONSTANT_Utf8:
                cp_info['tag'] = 'CONSTANT_Utf8'
                length = parse_u2(f);
                cp_info['bytes'] = f.read(length)
            elif tag == CONSTANT_Fieldref:
                cp_info['tag'] = 'CONSTANT_Fieldref'
                cp_info['class_index'] = parse_u2(f)
                cp_info['name_and_type_index'] = parse_u2(f)
            elif tag == CONSTANT_String:
                cp_info['tag'] = 'CONSTANT_String'
                cp_info['string_index'] = parse_u2(f)
            else:
                raise NotImplementedError(f"Unexpected constant tag {tag} in class file {file_path}")
            constant_pool.append(cp_info)
        clazz['constant_pool'] = constant_pool
        clazz['access_flags'] = parse_flags(parse_u2(f), class_access_flags)
        clazz['this_class'] = parse_u2(f)
        clazz['super_class'] = parse_u2(f)
        interfaces_count = parse_u2(f)
        interfaces: list[Any] = []
        for _ in range(interfaces_count):
            raise NotImplementedError("We don't support interfaces")
        clazz['interfaces'] = interfaces
        fields_count = parse_u2(f)
        fields: list[Any] = []
        for _ in range(fields_count):
            raise NotImplementedError("We don't support fields")
        clazz['fields'] = fields
        methods_count = parse_u2(f)
        methods = []
        for i in range(methods_count):
            # u2             access_flags;
            # u2             name_index;
            # u2             descriptor_index;
            # u2             attributes_count;
            # attribute_info attributes[attributes_count];
            method: dict[str, Any] = {}
            method['access_flags'] = parse_flags(parse_u2(f), method_access_flags)
            method['name_index'] = parse_u2(f)
            method['descriptor_index'] = parse_u2(f)
            attributes_count = parse_u2(f)
            method['attributes'] = parse_attributes(f, attributes_count)
            methods.append(method)
        clazz['methods'] = methods
        attributes_count = parse_u2(f)
        clazz['attributes'] = parse_attributes(f, attributes_count)
        return clazz

def find_methods_by_name(clazz: dict[str, Any], name: bytes) -> list[dict[str, Any]]:
    "Return methods from parsed class by name"
    return [method
            for method in clazz['methods']
            if clazz['constant_pool'][method['name_index'] - 1]['bytes'] == name]

def find_attributes_by_name(clazz: dict[str, Any],
                            attributes: list[dict[str, int | bytes]],
                            name: bytes) ->  list[dict[str, bytes]]:
    "Return attributes from parsed class by name"
    return [cast(dict[str, bytes], attr)
            for attr in attributes
            if clazz['constant_pool'][cast(int, attr['attribute_name_index']) - 1]['bytes'] == name]

def parse_code_info(info: bytes) -> dict[str, int | bytes]:
    "Parse code info"
    code: dict[str, int | bytes] = {}
    with io.BytesIO(info) as f:
        # Code_attribute {
        #     u2 attribute_name_index;
        #     u4 attribute_length;
        #     u2 max_stack;
        #     u2 max_locals;
        #     u4 code_length;
        #     u1 code[code_length];
        #     u2 exception_table_length;
        #     {   u2 start_pc;
        #         u2 end_pc;
        #         u2 handler_pc;
        #         u2 catch_type;
        #     } exception_table[exception_table_length];
        #     u2 attributes_count;
        #     attribute_info attributes[attributes_count];
        # }
        code['max_stack'] = parse_u2(f)
        code['max_locals'] = parse_u2(f)
        code_length = parse_u4(f)
        code['code'] = f.read(code_length)
        exception_table_length = parse_u2(f)
        # NOTE: parsing the code attribute is not finished
        return code

getstatic_opcode     = 0xB2
ldc_opcode           = 0x12
invokevirtual_opcode = 0xB6
return_opcode        = 0xB1
bipush_opcode        = 0x10

def get_name_of_class(clazz: dict[str, Any], class_index: int) -> str:
    "Get the name of a class"
    return cast(bytes, clazz['constant_pool'][clazz['constant_pool'][class_index - 1]['name_index'] - 1]['bytes']).decode('utf-8')

def get_name_of_member(clazz: dict[str, Any], name_and_type_index: int) -> str:
    "Get the name of a member of class"
    return cast(bytes, clazz['constant_pool'][clazz['constant_pool'][name_and_type_index - 1]['name_index'] - 1]['bytes']).decode('utf-8')

def execute_code(clazz: dict[str, Any], code: bytes) -> None:
    "Execute code in context of class"
    stack: list[dict[str, Any]] = []
    with io.BytesIO(code) as f:
        while f.tell() < len(code):
            opcode = parse_u1(f)
            if opcode == getstatic_opcode:
                index = parse_u2(f)
                fieldref = clazz['constant_pool'][index - 1]
                name_of_class = get_name_of_class(clazz, fieldref['class_index'])
                name_of_member = get_name_of_member(clazz, fieldref['name_and_type_index'])
                if name_of_class == 'java/lang/System' and name_of_member == 'out':
                    stack.append({'type': 'FakePrintStream'})
                else:
                    raise NotImplementedError(f"Unsupported member {name_of_class}/{name_of_member} in getstatic instruction")
            elif opcode == ldc_opcode:
                index = parse_u1(f)
                stack.append({'type': 'Constant', 'const': clazz['constant_pool'][index - 1]})
            elif opcode == invokevirtual_opcode:
                index = parse_u2(f)
                methodref = clazz['constant_pool'][index - 1]
                name_of_class = get_name_of_class(clazz, methodref['class_index'])
                name_of_member = get_name_of_member(clazz, methodref['name_and_type_index']);
                if name_of_class == 'java/io/PrintStream' and name_of_member == 'println':
                    n = len(stack)
                    if len(stack) < 2:
                        raise RuntimeError('{name_of_class}/{name_of_member} expectes 2 arguments, but provided {n}')
                    obj = stack[len(stack) - 2]
                    if obj['type'] != 'FakePrintStream':
                        raise NotImplementedError(f"Unsupported stream type {obj['type']}")
                    arg = stack[len(stack) - 1]
                    if arg['type'] == 'Constant':
                        if arg['const']['tag'] == 'CONSTANT_String':
                            print(clazz['constant_pool'][arg['const']['string_index'] - 1]['bytes'].decode('utf-8'))
                        else:
                            raise NotImplementedError(f"println for {arg['const']['tag']} is not implemented")
                    elif arg['type'] == 'Integer':
                        print(arg['value'])
                    else:
                        raise NotImplementedError(f"Support for {arg['type']} is not implemented")
                else:
                    raise NotImplementedError(f"Unknown method {name_of_class}/{name_of_member} in invokevirtual instruction")
            elif opcode == return_opcode:
                return
            elif opcode == bipush_opcode:
                byte = parse_u1(f)
                stack.append({'type': 'Integer', 'value': byte})
            else:
                raise NotImplementedError(f"Unknown opcode {hex(opcode)}")

if __name__ == '__main__':
    program, *args = sys.argv
    if len(args) == 0:
        print(f"Usage: {program} <path/to/Main.class>")
        print(f"ERROR: no path to Main.class was provided")
        exit(1)
    file_path, *args = args
    clazz = parse_class_file(file_path)
    [main] = find_methods_by_name(clazz, b'main')
    [code] = find_attributes_by_name(clazz, main['attributes'], b'Code')
    code_attrib = parse_code_info(code['info'])
    execute_code(clazz, code_attrib['code'])