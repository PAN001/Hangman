Strategy
1: guess
based
on
the
# - first guess based on the word-length based character frequency table
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