from pyhp.datatypes import W_IntObject, W_StringObject, \
    W_Null, W_Array, W_List, W_Boolean, W_FloatObject, W_Function, \
    W_CodeFunction
from pyhp.datatypes import compare_gt, compare_ge, compare_lt, compare_le, \
    compare_eq
from pyhp.datatypes import plus, increment, decrement, sub, mult, division

from pyhp.utils import printf

from rpython.rlib import jit


class Opcode(object):
    _settled_ = True

    def __init__(self):
        pass

    def get_name(self):
        return self.__class__.__name__

    def eval(self, frame):
        """ Execute in frame
        """
        raise NotImplementedError(self.get_name() + ".eval")

    def __str__(self):
        return self.get_name()


class LOAD_CONSTANT(Opcode):
    pass


class LOAD_VAR(Opcode):
    _immutable_fields_ = ['index', 'name']

    def __init__(self, index, name):
        self.index = index
        self.name = name

    def eval(self, frame):
        variable = frame.get_var(self.name, self.index)
        if variable is None:
            raise Exception("Variable %s (%s) is not set" %
                            (self.index, self.name))
        frame.push(variable)

    def __str__(self):
        return 'LOAD_VAR %s, %s' % (self.index, self.name)


class LOAD_FUNCTION(Opcode):
    _immutable_fields_ = ['function']

    def __init__(self, function):
        self.function = function

    def eval(self, frame):
        frame.push(W_CodeFunction(self.function))


class LOAD_LIST(Opcode):
    _immutable_fields_ = ['number']

    def __init__(self, number):
        self.number = number

    def eval(self, frame):
        list_w = frame.pop_n(self.number)
        frame.push(W_List(list_w))


class LOAD_NULL(Opcode):
    def eval(self, frame):
        frame.push(W_Null())

    def __str__(self):
        return 'LOAD_NULL'


class LOAD_BOOLEAN(Opcode):
    _immutable_fields_ = ['value']

    def __init__(self, value):
        self.value = W_Boolean(value)

    def eval(self, frame):
        frame.push(self.value)

    def __str__(self):
        return 'LOAD_BOOLEAN %s' % (self.value)


class LOAD_INTVAL(Opcode):
    _immutable_fields_ = ['value']

    def __init__(self, value):
        self.value = W_IntObject(value)

    def eval(self, frame):
        frame.push(self.value)

    def __str__(self):
        return 'LOAD_INTVAL %s' % (self.value)


class LOAD_FLOATVAL(Opcode):
    _immutable_fields_ = ['value']

    def __init__(self, value):
        self.value = W_FloatObject(value)

    def eval(self, frame):
        frame.push(self.value)

    def __str__(self):
        return 'LOAD_FLOATVAL %s' % (self.value)


class LOAD_STRINGVAL(Opcode):
    _immutable_fields_ = ['value']

    def __init__(self, value):
        self.value = W_StringObject(value)

    def eval(self, frame):
        stringval = self.value
        for variable in stringval.get_variables():
            search, identifier, indexes = variable
            value = frame.get_var(identifier)
            for key in indexes:
                if key[0] == '$':
                    key = frame.get_var(key).str()
                value = value.get(key)
            replace = value.str()
            stringval = stringval.replace(search, replace)

        frame.push(stringval)

    def __str__(self):
        return 'LOAD_STRINGVAL %s' % (self.value)


class LOAD_ARRAY(Opcode):
    _immutable_fields_ = ['number']

    def __init__(self, number):
        self.number = number

    @jit.unroll_safe
    def eval(self, frame):
        array = W_Array()
        list_w = frame.pop_n(self.number)
        for index, el in enumerate(list_w):
            array.put(str(index), el)
        frame.push(array)


class LOAD_MEMBER(Opcode):
    def eval(self, frame):
        array = frame.pop()
        member = frame.pop().str()
        value = array.get(member)
        frame.push(value)


class STORE_MEMBER(Opcode):
    def eval(self, frame):
        array = frame.pop()
        index = frame.pop().str()
        value = frame.pop()
        array.put(index, value)


class ASSIGN(Opcode):
    _immutable_fields_ = ['index', 'name']

    def __init__(self, index, name):
        self.index = index
        self.name = name

    def eval(self, frame):
        frame.set_var(self.index, self.name, frame.pop())

    def __str__(self):
        return 'ASSIGN %s, %s' % (self.index, self.name)


class DISCARD_TOP(Opcode):
    def eval(self, frame):
        frame.pop()


class DUP(Opcode):
    def eval(self, frame):
        frame.push(frame.top())


class BaseJump(Opcode):
    _immutable_fields_ = ['where']

    def __init__(self, where):
        self.where = where

    def eval(self, frame):
        pass


class JUMP_IF_FALSE(BaseJump):
    def do_jump(self, frame, pos):
        value = frame.pop()
        if not value.is_true():
            return self.where
        return pos + 1

    def __str__(self):
        return 'JUMP_IF_FALSE %d' % (self.where)


class JUMP(BaseJump):
    def do_jump(self, frame, pos):
        return self.where

    def __str__(self):
        return 'JUMP %d' % (self.where)


class RETURN(Opcode):
    def eval(self, frame):
        if frame.valuestack_pos > 0:
            return frame.pop()
        else:
            return W_Null()


class PRINT(Opcode):
    def eval(self, frame):
        item = frame.pop()
        printf(item.str())


class CALL(Opcode):
    def eval(self, frame):
        method = frame.pop()
        params = frame.pop()

        assert isinstance(method, W_Function)
        assert isinstance(params, W_List)

        res = method.call(params.to_list(), frame)
        frame.push(res)


class BaseDecision(Opcode):
    def eval(self, frame):
        right = frame.pop()
        left = frame.pop()
        res = self.decision(left, right)
        frame.push(W_Boolean(res))

    def decision(self, op1, op2):
        raise NotImplementedError


class EQ(BaseDecision):
    def decision(self, left, right):
        return compare_eq(left, right)


class GT(BaseDecision):
    def decision(self, left, right):
        return compare_gt(left, right)


class GE(BaseDecision):
    def decision(self, left, right):
        return compare_ge(left, right)


class LT(BaseDecision):
    def decision(self, left, right):
        return compare_lt(left, right)


class LE(BaseDecision):
    def decision(self, left, right):
        return compare_le(left, right)


class AND(BaseDecision):
    def decision(self, left, right):
        return left.is_true() and right.is_true()


class OR(BaseDecision):
    def decision(self, left, right):
        return left.is_true() or right.is_true()


class ADD(Opcode):
    def eval(self, frame):
        right = frame.pop()
        left = frame.pop()
        frame.push(plus(left, right))


class SUB(Opcode):
    def eval(self, frame):
        right = frame.pop()
        left = frame.pop()
        frame.push(sub(left, right))


class MUL(Opcode):
    def eval(self, frame):
        right = frame.pop()
        left = frame.pop()
        frame.push(mult(left, right))


class DIV(Opcode):
    def eval(self, frame):
        right = frame.pop()
        left = frame.pop()
        frame.push(division(left, right))


class BaseUnaryOperation(Opcode):
    pass


class NOT(BaseUnaryOperation):
    def eval(self, frame):
        val = frame.pop()
        boolval = val.is_true()
        frame.push(W_Boolean(not boolval))


class INCR(BaseUnaryOperation):
    def eval(self, frame):
        left = frame.pop()
        frame.push(increment(left))


class DECR(BaseUnaryOperation):
    def eval(self, frame):
        left = frame.pop()
        frame.push(decrement(left))


class MOD(Opcode):
    pass


class Opcodes:
    pass

# different opcode mappings, to make annotator happy

OpcodeMap = {}

for name, value in locals().items():
    if name.upper() == name and type(value) == type(Opcode) \
            and issubclass(value, Opcode):
        OpcodeMap[name] = value

opcodes = Opcodes()
for name, value in OpcodeMap.items():
    setattr(opcodes, name, value)
