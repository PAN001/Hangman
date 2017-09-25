from __future__ import division # force division to be floating point

import urllib2
import re as reg
import time
import yaml
import string

alphabets = ''.join(chr(x) for x in range(128))

class HangMan(object):
    def __init__(self, dict_path, freq_path, email):
        self.email = email

        # initialize all kinds of dicts or freq tables
        self.init_dicts(dict_path, freq_path)

    def init_dicts(self, dict_path, freq_path):
        """ initialize all kinds of dicts or freq tables
        """

        # generate universe character frequency table
        self.char_freq_table = ["e", "t", "a", "o", "i", "n", "s", "r", "h", "d", "l", "u", "c", "m", "f", "y", "w", "g",
                           "p", "b", "v", "k", "x", "q", "j", "z"]

        # load english word dict
        file = open(dict_path, "r")
        dictionary = file.read().split("\n")
        dictionary.remove("")
        dictionary = [word.lower() for word in dictionary]  # convert all to lower case
        self.dictionary = list(set(dictionary))  # remove all duplicates

        # load universe word frequency table
        file = open(freq_path, "r")
        self.freq_table = file.read().split("\n")

        # generate word-length based character frequency table
        max_length = len(max(self.dictionary, key=len))
        min_length = len(min(self.dictionary, key=len))
        length_range = max_length - min_length + 1

        words_by_size = []
        alphabets = string.ascii_lowercase
        word_len_freq_table = [[0] * len(alphabets) for i in range(length_range)] # length_range * len(alphabets)

        for i in range(0, length_range):
            words_i = self.group_by_size(self.dictionary, i + 1)
            words_by_size.append(words_i)
            for word in words_i:
                for j in range(0, len(alphabets)):
                    if alphabets[j] in word:
                        word_len_freq_table[i][j] = word_len_freq_table[i][j] + 1

        self.word_len_freq_table = word_len_freq_table

    def do_guess(self, state, chars_guess_wrong, chars_guess_all):
        """ Strategy:
            - choose the most frequent character in all potentially matched words each time
            - first guess based on the word-length based character frequency table
            - adjust the weight based on universe word frequency table:
                When obsscured chars become fewer, it is hard to select simply based on the character frequency.
                For example: 'THE EMBRACE O_ THE BREASTS':
                It will return a character frequency table: {'g': 1, 'f': 1, 'k': 1, 'l': 1, 'n': 1, 'p': 1, 'u': 1, 'w': 1, 'v': 1, 'y': 1, 'x': 1, 'z': 1}
                it is hard to choose the correct word in this case. This problem can be fixed by adjusting the frequency weight based on the frequency of the
                potentially matched words. Larger weight is given to the specific char if the potentially matched word with this char has larger word frequency.
            - increase the weight if the potentially matched word list is small

            Apart from what mentioned above, the strategy also adapts dynamically. For example, it will not increase the weight when the number of obscured chars has not
            arrived certain threshold even if the potentially matched word list is small.

            This only gives a big idea of how to guess. There are several hyper-parameters need to be fine-tunes in practice, such as the weight and threshold.
        """
        words = state.split(" ")
        char_weights = {}
        num_obscured_all = state.count("_")
        guess = ""

        if chars_guess_all == "": # first guess: base on the word_len_freq_table
            print "first guess"
            for word in words:
                if(len(word) > len(self.word_len_freq_table)):
                    continue;
                cur_len_freqs = self.word_len_freq_table[len(word) + 1]
                index = cur_len_freqs.index(max(cur_len_freqs))
                matched_char = chr(ord('a') + index)
                if matched_char in char_weights:
                    char_weights[matched_char] = char_weights[matched_char] + 1  # update the frequency weight
                else:
                    char_weights[matched_char] = 1

            guess = str(max(char_weights, key  =char_weights.get))
            return guess

        # guess the word one by one
        for word in words:
            num_obscured = word.count("_")
            word = word.lower()
            if word.find("_") != -1:
                temp = word
                reg_exp = "^"
                reg_exp = temp.replace("_", "[a-z]")
                if chars_guess_wrong != "":
                    reg_exp = word.replace("_",
                                           "(?![" + chars_guess_wrong + "])[a-z]")  # ignore those words with wrong guessed characters

                reg_exp = reg_exp + "$"
                matched_words = []
                for dic_word in self.dictionary:
                    if len(dic_word) == len(word):  # if the word in diction has the same length
                        # use RE to search potential words in the dictionary
                        matched_word_dic = reg.search(reg_exp, dic_word, reg.IGNORECASE)
                        if matched_word_dic is not None:
                            matched_word_dic = matched_word_dic.group(0)
                            matched_words.append(matched_word_dic)

                for matched_word_dic in matched_words:
                    weight = 1
                    if num_obscured <= 2 and (
                        matched_word_dic in self.freq_table):  # use frequency weight strategy only when there are fewer obscured chars left
                        weight = self.scale(len(self.freq_table) - self.freq_table.index(matched_word_dic), 0, 10000, 1.5, 2)  # scale down the weight to [1.5, 2]
                        # print matched_word_dic, ": ", weight
                    if num_obscured_all <= 2 and len(
                            matched_word_dic) <= 2:  # if there are very few matched words, increase of the weight since this char is more likely to be matched
                        weight = weight * 1.5
                    for i in range(0, len(word)):  # check every character in current word
                        distinct_chars = set()
                        if word[i] == '_':  # if the character at position i has not been found
                            matched_char = matched_word_dic[i].lower()
                            if matched_char in chars_guess_all or matched_char in distinct_chars:  # if this char has already been guessed or the word has already contained this char, the weight should ne bot updated
                                continue;

                            if matched_char in char_weights:
                                char_weights[matched_char] = char_weights[matched_char] + weight  # update the frequency weight
                            else:
                                char_weights[matched_char] = weight

                                # if num_obscured_all <= 2:
                                #     print char_weights

        if not char_weights:  # if the obscured word is not in the word list at first place, simply guess based on the universe character frequency
            for x in self.char_freq_table:
                if not (x in chars_guess_all):
                    guess = x
        else:
            max_char = str(max(char_weights, key=char_weights.get))  # return the character of the biggest frequency
            while max_char.lower() in chars_guess_all:  # if the character has already been guessed
                del char_weights[max_char]  # find next one
                max_char = str(max(char_weights, key=char_weights.get))
            guess = max_char
        return guess


    def run(self):
        """Run the game simulation
        """
        is_in_progress = False
        remaining_guesses = 3
        round_cnt = 0
        num_rounds = 50
        chars_guess_wrong = ""
        chars_guess_correct = ""
        chars_guess_all = ""
        guess = ""
        data = []
        num_death = 0
        num_guesses = 0
        while round_cnt < num_rounds:
            if not is_in_progress:  # a new round game
                print "new guess"
                url = "http://gallows.hulu.com/play?code=" + self.email
                d = urllib2.urlopen(url)
                data = yaml.safe_load(d)
                print data

                # reinitialize the variables
                chars_guess_wrong = ""
                chars_guess_correct = ""
                chars_guess_all = ""
                guess = ""
                remaining_guesses = 3
                is_in_progress = True
                round_cnt = round_cnt + 1
            else:
                print "next guess"
                token = data['token']
                guess = self.do_guess(data['state'], chars_guess_wrong, chars_guess_all).lower()
                num_guesses = num_guesses + 1
                url = "http://gallows.hulu.com/play?code=" + self.email + "&token=" + token + "&guess=" + guess
                d = urllib2.urlopen(url)
                data = yaml.safe_load(d)
                print "updated data: ", data
                new_remaining_guesses = data["remaining_guesses"]
                if new_remaining_guesses == remaining_guesses - 1:  # wrong guess
                    print "wrong guess: ", guess
                    chars_guess_wrong = chars_guess_wrong + guess
                elif new_remaining_guesses == remaining_guesses:
                    print "correct guess: ", guess
                    chars_guess_correct = chars_guess_correct + guess

                remaining_guesses = new_remaining_guesses
                chars_guess_all = chars_guess_all + guess
                if data['status'] == 'FREE':
                    is_in_progress = False
                elif data['status'] == 'DEAD':
                    print "Bomb: dead ", num_death
                    num_death = num_death + 1
                    is_in_progress = False

            time.sleep(1)  # sleep for one second

        print "Total death: ", num_death

    # helper functions
    def group_by_size(self, words, size):
        """Group word by its size
        """
        return [word for word in words if len(word) == size]

    def all_indices(value, qlist):
        """Find all the indices of the given element in the list
        """
        indices = []
        idx = -1
        while True:
            try:
                idx = qlist.index(value, idx + 1)
                indices.append(idx)
            except ValueError:
                break
        return indices

    def scale(self, valueIn, baseMin, baseMax, limitMin, limitMax):
        """Scale the value to a specific range
        """
        scaled_val = ((limitMax - limitMin) * (valueIn - baseMin) / (baseMax - baseMin)) + limitMin
        return scaled_val

def main():
    dict_path = "words.txt"
    freq_path = "google-10000-english-usa-no-swears.txt"
    email = "panatopos@cmu.edu"
    game = HangMan(dict_path, freq_path, email)
    game.run()

if __name__ == "__main__":
    main()

#
# # def generate_frequency_table():
# max_length = len(max(dictionary, key=len))
# min_length = len(min(dictionary, key=len))
# length_range = max_length - min_length + 1
#
# words_by_size = []
# frequency_table = [[0] * len(alphabets) for i in range(length_range)] # length_range * len(alphabets)
#
# for i in range(0, length_range):
#     words_i = by_size(dictionary, i + 1)
#     words_by_size.append(words_i)
#     for word in words_i:
#         letter_index = 0
#         for j in range(0, len(alphabets)):
#             if alphabets[j] in word:
#                 frequency_table[i][j] = frequency_table[i][j] + 1
#
#
# x = all_indices(1, frequency_table[0])
# y = [chr(ord('0') + x[i]) for i in range(0, len(x))]







# # email = "panatopos@cmu.edu"
# is_in_progress = False
# remaining_guesses = 3
# round_cnt = 0
# num_rounds = 50
# # results = []
# chars_guess_wrong = ""
# chars_guess_correct = ""
# chars_guess_all = ""
# guess = ""
# dic_path = "words.txt"
# freq_path = "google-10000-english-usa-no-swears.txt"
# file = open(dic_path, "r")
# dictionary = file.read().split("\n")
# dictionary.remove("")
# dictionary = [word.lower() for word in dictionary] # convert all to lower case
# dictionary = list(set(dictionary)) # remove all duplicates
# file = open(freq_path, "r")
# freq_table = file.read().split("\n")
# # freq_table.remove("")
# char_freq_table = ["e", "t", "a", "o", "i", "n", "s", "r", "h", "d", "l", "u", "c", "m", "f", "y", "w", "g", "p", "b", "v", "k", "x", "q", "j", "z"]
#
# data = []
#
# num_death = 0
# num_guesses = 0


# Strategy 1: guess based on the
# - adjust the weight based on universe word frequency table:
#       When obsscured chars become fewer, it is hard to select simply based on the character frequency:
#       for example: 'THE EMBRACE O_ THE BREASTS'
#       it will return a character frequency table: {'g': 1, 'f': 1, 'k': 1, 'l': 1, 'n': 1, 'p': 1, 'u': 1, 'w': 1, 'v': 1, 'y': 1, 'x': 1, 'z': 1}
#       it is hard to choose the correct word in this case. This problem can be fixed by adjusting the frequency weight based on the frequency of the
#       potentially matched words. Larger weight is given to the specific char if the potentially matched word with this char has larger word frequency.
#
# - increase the weight if the potentially matched word list is small

# Apart from mentioned above, the strategy also adapts dynamically. For example, it will not increase the weight when the number of obscured chars has not
# arrived certain threshold even if the potentially matched word list is small.

# def guess_1(state, chars_guess_all):
#     words = state.split(" ")
#     char_weights = {}
#     num_obscured_all = state.count("_")
#     print(num_obscured_all)
#
#     # guess the word one by one
#     for word in words:
#         num_obscured = word.count("_")
#         word = word.lower()
#         # print temp
#         if word.find("_") != -1:
#             temp = word
#             reg_exp = "^"
#             reg_exp = temp.replace("_", "[a-z]")
#             if chars_guess_wrong != "":
#                 reg_exp = word.replace("_", "(?![" + chars_guess_wrong + "])[a-z]") # ignore those words with wrong guessed characters
#
#             reg_exp = reg_exp + "$"
#             matched_words = []
#             for dic_word in dictionary:
#                 if len(dic_word) == len(word):  # if the word in diction has the same length
#                     # use RE to search potential words in the dictionary
#                     matched_word_dic = reg.search(reg_exp, dic_word, reg.IGNORECASE)
#                     if matched_word_dic is not None:
#                         matched_word_dic = matched_word_dic.group(0)
#                         matched_words.append(matched_word_dic)
#
#             for matched_word_dic in matched_words:
#                 weight = 1
#                 if num_obscured <= 2 and (matched_word_dic in freq_table): # use frequency weight strategy only when there are fewer obscured chars left
#                     weight = scale(len(freq_table) - freq_table.index(matched_word_dic), 0, 10000, 1.5, 2) # scale down the weight to [1.5, 2]
#                     # print matched_word_dic, ": ", weight
#                 if num_obscured_all <= 2 and len(matched_word_dic) <= 2: # if there are very few matched words, increase of the weight since this char is more likely to be matched
#                     weight = weight * 1.5
#                 for i in range(0, len(word)):  # check every character in current word
#                     distinct_chars = set()
#                     if word[i] == '_':  # if the character at position i has not been found
#                         foundChar = matched_word_dic[i].lower()
#                         if foundChar in chars_guess_all or foundChar in distinct_chars: # if this char has already been guessed or the word has already contained this char, the weight should ne bot updated
#                             continue;
#
#                         if foundChar in char_weights:
#                             char_weights[foundChar] = char_weights[foundChar] + weight  # update the frequency weight
#                         else:
#                             char_weights[foundChar] = weight
#
#                         # if num_obscured_all <= 2:
#                         #     print char_weights
#
#     if not char_weights: # if the obscured word is not in the word list at first place, simply guess based on the universe character frequency
#         for x in range(0, 26):
#             if not (x in chars_guess_all):
#                 guess = x
#     else:
#         maxChar = str(max(char_weights, key = char_weights.get))  # return the character of the biggest frequency
#         while maxChar.lower() in chars_guess_all:  # if the character has already been guessed
#             del char_weights[maxChar]  # find next one
#             maxChar = str(max(char_weights, key = char_weights.get))
#         guess = maxChar
#     return guess
#
# while round_cnt < num_rounds:
#     if not is_in_progress:  # a new round game
#         print "new guess"
#         url = "http://gallows.hulu.com/play?code=panatopos@cmu.edu"
#         d = urllib2.urlopen(url)
#         data = yaml.safe_load(d)
#         print data
#
#         # initialize the global variables
#         chars_guess_wrong = ""
#         chars_guess_correct = ""
#         chars_guess_all = ""
#         guess = ""
#         remaining_guesses = 3
#         # options = {
#         #     'status': data['status'],
#         #     'token': data['token'],
#         #     'remaining_guesses': data['remaining_guesses'],
#         #     'state': data['state'],
#         #     'results': results
#         # }
#         is_in_progress = True
#         round_cnt = round_cnt + 1
#     else:
#         print "next guess"
#         token = data['token']
#         guess = guess_1(data['state'], chars_guess_all).lower()
#         num_guesses = num_guesses + 1
#         print "next guess is: " + guess
#         url = "http://gallows.hulu.com/play?code=panatopos@cmu.edu&token=" + token + "&guess=" + guess
#         d = urllib2.urlopen(url)
#         data = yaml.safe_load(d)
#         print "updated data: ", data
#         new_remaining_guesses = data["remaining_guesses"]
#         if new_remaining_guesses == remaining_guesses - 1:  # wrong guess
#             print "wrong guess: ", guess
#             chars_guess_wrong = chars_guess_wrong + guess
#         elif new_remaining_guesses == remaining_guesses:
#             print "correct guess: ", guess
#             chars_guess_correct = chars_guess_correct + guess
#
#
#         remaining_guesses = new_remaining_guesses
#         # results.append("Guessing '" + guess + "'")
#         # options = {
#         #     'status': data['status'],
#         #     'token': data['token'],
#         #     'remaining_guesses': data['remaining_guesses'],
#         #     'state': data['state'],
#         #     'results': results
#         # }
#         chars_guess_all = chars_guess_all + guess
#         if data['status'] == 'FREE':
#             is_in_progress = False
#         elif data['status'] == 'DEAD':
#             print "Bomb: dead ", num_death
#             num_death = num_death + 1
#             is_in_progress = False
#
#     time.sleep(1)  # sleep for one second