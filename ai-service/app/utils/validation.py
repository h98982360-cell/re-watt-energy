import re

# matches whole numbers and decimals, like 500, 2,150 or 12.5
NUMBER = re.compile(r"\d[\d,]*\.?\d*")

# small numbers that a model might spell out, like "four suppliers"
WORD_NUMBERS = {
    "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
    "seven": 7, "eight": 8, "nine": 9, "ten": 10,
}
WORD = re.compile(r"\b(" + "|".join(WORD_NUMBERS) + r")\b", re.IGNORECASE)

def numbers_in(text: str) -> set[float]:
    # numbers written as digits, ignoring thousands commas
    digits = {float(n.replace(",", "").rstrip(".")) for n in NUMBER.findall(text)}

    # numbers written as words, converted to their digit value
    words = {float(WORD_NUMBERS[w.lower()]) for w in WORD.findall(text)}
    return digits | words

# Function to check if the output contains any number that was not in the input
def has_invented_numbers(output_text: str, input_text: str) -> bool:
    # true if the output contains any number that was not in the input
    return not numbers_in(output_text) <= numbers_in(input_text)