#!/usr/bin/python
# -*- coding: utf8 -*-
import json
import os
import random
from datetime import datetime

dir_path = os.path.dirname(os.path.realpath(__file__))
data_file_path = os.path.join(dir_path, './persist/iching.json')
with open(data_file_path, encoding='utf8') as f:
    data = json.load(f)

trigram_sequences = {
    'earlierHeaven': [1, 6, 4, 5, 2, 3, 7, 8],
    'laterHeaven': [7, 2, 8, 1, 4, 5, 3, 6]
}

class IChing:
    def __init__(self):
        self.trigrams = [Trigram(n, self) for n in range(1, 9)]
        self.hexagrams = [Hexagram(n, self) for n in range(1, 65)]
        self._graph = None

    def trigram(self, number):
        assert_valid_trigram_number(number)
        return self.trigrams[number - 1]

    def trigramSequence(self, name):
        if name not in trigram_sequences:
            raise ValueError('name must be a trigram sequence name')
        return [self.trigram(n) for n in trigram_sequences[name]]

    def hexagram(self, number):
        assert_valid_hexagram_number(number)
        return self.hexagrams[number - 1]

    def ask(self, question):
        return Reading(question, self)

    def asGraph(self):
        if self._graph:
            return self._graph
        graph = {'nodes': [], 'edges': []}
        for t in self.trigrams:
            graph['nodes'].append(
                {'id': 't' + str(t.number), 'type': 'trigram', 'name': t.character, 'number': t.number})
        for h in self.hexagrams:
            id = 'h' + str(h.number)
            graph['nodes'].append({'id': id, 'type': 'hexagram', 'name': h.character, 'number': h.number})
            graph['edges'].append(
                {'id': f"{id}-t{h.bottomTrigram.number}-bottom", 'from': id, 'to': 't' + str(h.bottomTrigram.number),
                 'name': 'bottom'})
            graph['edges'].append(
                {'id': f"{id}-t{h.topTrigram.number}-top", 'from': id, 'to': 't' + str(h.topTrigram.number),
                 'name': 'top'})
            changes = h.changes
            for c in changes:
                graph['edges'].append(
                    {'id': f"{id}-h{c.to_hexagram.number}", 'from': id, 'to': 'h' + str(c.to_hexagram.number),
                     'name': c.binary})
        self._graph = graph
        return graph


class Trigram:
    def __init__(self, number, iching):
        assert_valid_trigram_number(number)
        self.iching = iching
        for key, value in data['trigrams'][number - 1].items():
            setattr(self, key, value)

    def hexagrams(self, position=None):
        if position and position not in ['top', 'bottom']:
            raise ValueError('position must be "top", "bottom", or None')
        return [h for h in self.iching.hexagrams if
                (h.topTrigram.number == self.number and (position is None or position == 'top')) or
                (h.bottomTrigram.number == self.number and (position is None or position == 'bottom'))]


class Change:
    def __init__(self, from_hexagram, to_hexagram):
        if not isinstance(from_hexagram, Hexagram):
            assert_valid_hexagram_number(from_hexagram)
            from_hexagram = from_hexagram.iching.hexagram(from_hexagram)
        self.from_hexagram = from_hexagram

        if not isinstance(to_hexagram, Hexagram):
            assert_valid_hexagram_number(to_hexagram)
            to_hexagram = to_hexagram.iching.hexagram(to_hexagram)
        self.to_hexagram = to_hexagram

        change_value = int(from_hexagram.binary, 2) ^ int(to_hexagram.binary, 2)  # xor
        self.binary = to_binary_string(change_value)
        self.changing_lines = [int(char) for char in self.binary][::-1]


class Hexagram:
    def __init__(self, number, iching):
        self.number = number
        assert_valid_hexagram_number(number)
        self.iching = iching
        self.binary = to_binary_string(self.number)
        for key, value in data['hexagrams'][number - 1].items():
            if key == 'topTrigram':
                self.topTrigram = self.iching.trigram(value)
            elif key == 'bottomTrigram':
                self.bottomTrigram = self.iching.trigram(value)
            else:
                setattr(self, key, value)

    def change_to(self, number):
        assert_valid_hexagram_number(number)
        if self.number == number:
            return None
        h2 = self.iching.hexagram(number)
        return Change(self, h2)

    def change_lines(self, lines):
        if not isinstance(lines, list) or len(lines) != 6:
            raise ValueError('lines argument must be a list of 6 zeros and ones representing changing lines')

        other_binary = ''
        changing_lines = lines[::-1]
        this_lines = self.lines[::-1]
        for l, c in zip(this_lines, changing_lines):
            if not isinstance(l, int) or l < 0 or l > 1:
                raise ValueError('lines argument must be a list of 6 zeros and ones representing changing lines')
            other_binary += str(l ^ c)  # xor

        if other_binary == self.binary:
            return None

        other_hexagram = next((h for h in self.iching.hexagrams if h.binary == other_binary), None)

        return Change(self, other_hexagram)

    @property
    def changes(self):
        if not hasattr(self, '_changes'):
            self._changes = [Change(self, h2) for h2 in range(1, 65) if (Change(self, h2).binary != '000000')]
        return self._changes


class Reading:
    def __init__(self, question, iching):
        self.iching = iching
        rng = random.Random()
        now = datetime.now()
        seed = question +" in this time: "+ now.strftime("%y%m%d%H%M%S")
        rng.seed(seed)

        hexagram_lines = []
        changing_lines = []
        for l in range(1, 7):
            line = self.generate_line(rng)
            if line == 9:
                hexagram_lines.append(1)
                changing_lines.append(1)
            elif line == 8:
                hexagram_lines.append(0)
                changing_lines.append(0)
            elif line == 7:
                hexagram_lines.append(1)
                changing_lines.append(0)
            elif line == 6:
                hexagram_lines.append(0)
                changing_lines.append(1)
            else:
                raise ValueError('unknown line: ' + str(line))

        self.hexagram = next((h for h in self.iching.hexagrams if h.lines == hexagram_lines), None)
        if not self.hexagram:
            raise ValueError('no reading could be obtained')

        self.change = self.hexagram.change_lines(changing_lines)

    def generate_line(self, rng):
        num_stalks = 49
        line_sum = 0
        for _ in range(3):
            composite = self.generate_composite(num_stalks, rng)
            num_stalks -= composite['stalksUsed']
            line_sum += composite['number']
        return line_sum

    def generate_composite(self, num_stalks, rng):
        left_pile_size = int(rng.uniform(4, num_stalks - 5))
        right_pile_size = num_stalks - left_pile_size

        right_pile_size -= 1
        stalks_used = 1

        r = self.get_remainder(left_pile_size)
        left_pile_size -= r
        stalks_used += r

        r = self.get_remainder(right_pile_size)
        right_pile_size -= r
        stalks_used += r

        composite = {'stalksUsed': stalks_used}

        if stalks_used in [9, 8]:
            composite['number'] = 2
        elif stalks_used in [5, 4]:
            composite['number'] = 3
        else:
            raise ValueError('unknown number = ' + str(stalks_used))

        return composite

    def get_remainder(self, pile_size):
        r = pile_size % 4
        return r if r != 0 else 4


def assert_valid_trigram_number(number):
    if not isinstance(number, int) or number < 1 or number > 8:
        raise ValueError('number must be an integer between 1 and 8')


def assert_valid_hexagram_number(number):
    if not isinstance(number, int) or number < 1 or number > 64:
        raise ValueError('number must be an integer between 1 and 64')


def to_binary_string(i):
    return pad(bin(i)[2:], 6)


def pad(num, size):
    return num.zfill(size)






def extract_iching(question: str) -> str:
    iChing = IChing()
    reading = iChing.ask(question)
    return f"{reading.hexagram.number} {reading.hexagram.character} {', '.join(reading.hexagram.names)}\n\n\nJudgement:\n{reading.hexagram.judgement}\n\nImages:\n{reading.hexagram.images}"

def prophet_iching(question: str) -> str:
    iChing = IChing()
    reading = iChing.ask(question)
    changing = ''


    if reading.change:
        for index, value in enumerate(reading.change.changing_lines):
            if value == 1:
                descriptions = reading.change.from_hexagram.linesDescription
                changing += f"\nChanging in line {index + 1}:" + f" {descriptions[index]['meaning']}"

    if not changing:
        changing = "\n\nNo Change"
    else:
        changing += (
                "\n\nChanging to:" +
                f" {reading.change.to_hexagram.number}" +
                f" {reading.change.to_hexagram.character}" +
                f" {', '.join(reading.change.to_hexagram.names)}" +
                f"\n\n\nJudgement:\n{reading.change.to_hexagram.judgement}" +
                f"\n\nImages:\n{reading.change.to_hexagram.images}"
        )

    return f"{reading.hexagram.number} {reading.hexagram.character} {', '.join(reading.hexagram.names)}\n\n\nJudgement:\n{reading.hexagram.judgement}\n\nImages:\n{reading.hexagram.images}{changing}"

def main():
    print(prophet_iching("Domanda asd"))


if __name__ == '__main__':
    main()
