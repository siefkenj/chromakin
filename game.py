'''
Created on Aug 13, 2012

@author: cheesinglee
'''

from __future__ import print_function
from random import shuffle, sample, random
from itertools import combinations_with_replacement
import sys
from copy import deepcopy

if sys.version_info.major == 2:
    input = raw_input

# define scoring schemes
scoring1 = [0,1,3,6,10,15,21]
scoring2 = [0,1,4,8,7,6,5]

class ChromakinGame(object):
    '''
    Class which implements the logic for the Chromakin game
    '''


    deck = []
    players = []
    two_player = False
    colors = ['green','blue','brown','yellow','gray','pink','orange']
    piles = []
    piles_taken = []
    scoring = []
    log_buffer = ''
    log_mode = 'buffer'
    log_filename = ''

    def __init__(self,players,scoring):
        self.scoring = scoring
        self.players = players
        self.two_player = len(self.players) == 2
        if not self.two_player:
            self.piles = [list() for p in self.players]
        else:
            self.piles = [list(),list(),list()]

    def initialize_deck(self):
        """ populate the Chromakin deck """

        # 7 colors (if >3 players, 6 if >2 players, else 5 colors), 9 of each
        reduce_colors_by = 2 if len(self.players) == 2 else 1 if len(self.players) == 3 else 0
        self.deck = self.colors[reduce_colors_by:]*9
        self.colors = self.colors[reduce_colors_by:]

        # 3 wilds
        self.deck.extend(['wild']*3)

        # 10 bonus "+2" cards
        self.deck.extend(['+2']*10)

        # shuffle
        shuffle(self.deck)
        
        # initialize player cards
        unique_cards = set(self.deck)
        for p in self.players:
            p.cards = dict(zip(unique_cards,list([0])*len(unique_cards)))

    def play(self):
        """ Play one game of Chromakin
        """
        self.initialize_deck()
        if not self.two_player:
            self.piles = [list() for p in self.players]
        else:
            self.piles = [list(),list(),list()]
        n_players = len(self.players)
        # deal initial colors
        if not self.two_player:
            start_colors = sample(self.colors,n_players)
            for i in range(n_players):
                self.players[i].take_cards([start_colors[i]])
                self.deck.remove(start_colors[i])
        else:
            start_colors = sample(self.colors,4)
            self.players[0].take_cards(start_colors[0:2])
            self.players[1].take_cards(start_colors[2:])
            for i in range(4):
                self.deck.remove(start_colors[i])
        shuffle(self.deck)

        last_round = False
        player_idx = -1
        n_rounds = 0
        while not last_round:
            n_rounds += 1
            self.log('\n----Round '+str(n_rounds)+'----')
            # clear the piles
            if not self.two_player:
                self.piles = [list() for p in self.players]
            else:
                self.piles = [list(),list(),list()]
            # all players are in again
            if not self.two_player:
                self.piles_taken = [False]*n_players
            else:
                self.piles_taken = [False]*3
            for p in self.players:
                p.out = False
                self.print_player_status(p)
            all_out = False
            while not all_out:
                # choose next player
                while True:
                    player_idx += 1
                    if player_idx == n_players:
                        player_idx = 0
                    if not self.players[player_idx].out:
                        break
                player = self.players[player_idx]
                self.log("\nIt's "+player.name+"'s turn")
                self.print_piles()
                self.update_players()
                if not any(self.piles):
                    # all piles are empty, player must draw
                    self.log('All piles are empty, draw a card')
                    c = self.deck.pop(0)
                    self.log('Drew a '+c)
                    pile_idx = player.select_pile(c)
                    self.piles[pile_idx].append(c)
                    self.log('Placed on pile '+str(pile_idx))
                elif self.all_piles_full():
                    # all available piles full, player must take one
                    self.log('All available piles are full')
                    pile_idx = player.select_pile()
                    player.take_cards(self.piles[pile_idx])
                    self.piles[pile_idx] = []
                    self.piles_taken[pile_idx] = True
                    self.log(player.name+' takes pile '+str(pile_idx))
                    player.out = True
                else:
                    # player can choose an action
                    action = player.get_action()
                    if action == 'take':
                        pile_idx = player.select_pile()
                        player.take_cards(self.piles[pile_idx])
                        self.piles[pile_idx] = []
                        self.piles_taken[pile_idx] = True
                        self.log(player.name+' takes pile '+str(pile_idx))
                        player.out = True
                    elif action == 'draw':
                        c = self.deck.pop(0)
                        self.log('Drew a '+c)
                        pile_idx = player.select_pile(c)
                        self.piles[pile_idx].append(c)
                        self.log('Placed on pile '+str(pile_idx))
                # check for last round
                cards_left = len(self.deck)
                self.log('Cards left: '+str(cards_left))
                if cards_left < 15:
                    self.log('Last Round!')
                    last_round = True
                # check if everyone is out
                all_out = True
                for p in self.players:
                    all_out = all_out and p.out
            # adjust the player index so that the last player to take in this
            # round is the starting player for the next round
            player_idx -= 1
        self.log('\n----Game Over----')
        final_scores = self.compute_scores()
        for p in self.players:
            p.end_game()
            p.out = False
            self.print_player_status(p)
        self.log('Remaining cards: '+str(self.deck))
        # determine the winner
        winner = 0
        for i in range(n_players):
            if final_scores[i] > final_scores[winner]:
                winner = i
        self.log(self.players[winner].name+' is the winner')

    @staticmethod
    def score(cards,scoring):
        """ compute scores for a set of cards
        """

        # get the number of color cards
        colors = []
        color_counts_no_wild = []
        for (c,n) in cards.items():
            if c != 'wild' and c[0] != '+' and c[0] != '-':
                colors.append(c)
                color_counts_no_wild.append(n)
        
        # assign wilds
        # TODO: find optimal wild assignment in a not brute force manner
        n_wilds = cards['wild']
        score = -1
        if n_wilds > 0:
            max_score = -1
            for wild_assignments in \
            combinations_with_replacement(range(len(colors)),n_wilds):
                # make a copy of the wild-less color counts
                color_counts = list(color_counts_no_wild)

                # make the wild assignments
                for i in wild_assignments:
                    color_counts[i] += 1
               
                # truncate the color counts if the exceed the defined values 
                # in the scoring scheme
                for i in range(len(color_counts)):
                    if color_counts[i] >= len(scoring):
                        color_counts[i] = len(scoring)-1
                
                # compute scoring
                values = [scoring[n] for n in color_counts]
                values.sort(reverse=True)
                tmp_score = 0
                for (n,v) in enumerate(values):
                    if n < 3:
                        tmp_score += v
                    else:
                        tmp_score -= v
                if tmp_score > max_score:
                    max_score = tmp_score
            score = max_score
        else:
            # truncate the color counts if the exceed the defined values 
            # in the scoring scheme
            for i in range(len(color_counts_no_wild)):
                if color_counts_no_wild[i] >= len(scoring):
                    color_counts_no_wild[i] = len(scoring)-1
            # scoring without wilds
            values = [scoring[n] for n in color_counts_no_wild]
            values.sort(reverse=True)
            score = 0
            for (n,v) in enumerate(values):
                if n < 3:
                    score += v
                else:
                    score -= v

        # add bonus cards
        for (name,count) in cards.items():
            try:
                bonus_value = float(name)
                score += bonus_value*count
            except ValueError:
                pass
             
        return score


    def compute_scores(self):
        player_scores = []
        for p in self.players:
            s = self.score(p.cards,self.scoring)
            player_scores.append(s)
        return player_scores
    
    def get_game_state(self):
        game_state = {}
        cards = [deepcopy(other_p.cards) for other_p in self.players]
        game_state['cards'] = cards
        game_state['scoring'] = deepcopy(self.scoring)
        game_state['piles'] = deepcopy(self.piles)
        game_state['piles_taken'] = deepcopy(self.piles_taken)
        game_state['two_player'] = self.two_player
        return game_state
    
    def update_players(self):
        game_state = self.get_game_state()
        for p in self.players:
            opponent_cards = [deepcopy(other_p.cards) for other_p in self.players \
                              if other_p is not p]
            p.update(game_state)

    def all_piles_full(self):
        """ check if all available piles are full """
        if not self.two_player:
            n_players = len(self.players)
            full = [len(self.piles[i])==3 for i in range(n_players) if not self.piles_taken[i]]
            return all(full)
        else:
            return (
                (len(self.piles[0]) == 1 or self.piles_taken[0]) and
                (len(self.piles[1]) == 2 or self.piles_taken[1]) and
                (len(self.piles[2]) == 3 or self.piles_taken[2]))

    def set_log_mode(self,mode,filename=''):
        if mode == 'buffer' or mode == 'print' or mode == 'file':
            self.log_mode = mode
            self.log_filename = ''
        else:
            raise(ValueError,'acceptable log modes are "buffer", "print", or "file"')

    def log(self,s):
        if self.log_mode == 'buffer':
            self.log_buffer += s+'\n'
        elif self.log_mode == 'print':
            print(s)
        elif self.log_mode == 'file':
            try:
                fid = open(s,'a')
                fid.write(s+'\n')
                fid.close()
            except:
                print('Error, could not write log to file '+self.log_dest)
                
    def flush_log(self):
        flushed = self.log_buffer
        self.log_buffer = ''
        return flushed

    def print_player_status(self,p):
        score = self.score(p.cards,self.scoring)
        s = p.name+':\t'+str(score)+' points\n'
        for color in p.cards.keys():
            s += color+'\t'
        s += '\n'
        for count in p.cards.values():
            s += str(count)+'\t'
#        cards = list(p.cards)
#        cards.sort()
#
#        template = '{name}:\t{score} points\n\
#        Orange: {n_orange}\tBlue: {n_blue}\tBrown: {n_brown}\n\
#        Yellow: {n_yellow}\tGray: {n_gray}\tGreen: {n_green}\n\
#        Pink  : {n_pink}\tWild: {n_wild}\t+2   : {n_bonus}'
#        s = template.format(name=p.name,score=str(score),
#                            n_orange=str(cards.count('orange')),
#                            n_blue=str(cards.count('blue')),
#                            n_brown=str(cards.count('brown')),
#                            n_yellow=str(cards.count('yellow')),
#                            n_gray=str(cards.count('gray')),
#                            n_green=str(cards.count('green')),
#                            n_pink=str(cards.count('pink')),
#                            n_wild=str(cards.count('wild')),
#                            n_bonus=str(cards.count('+2')))
        self.log(s)

    def print_piles(self):
        s = 'Pile contents: \n'
        for i in range(len(self.piles)):
            if not self.piles_taken[i]:
                s += str(i)+':'+str(self.piles[i])+' '
            else:
                s += str(i)+':'+'[TAKEN] '
        self.log(s)

    def get_piles_take(self):
        """ get the piles which can be taken

        Returns a tuple (P,I), where P is a list of the available piles, and
        I is a list of indices corresponding to the full list of piles.

        """
        idx_take = []
        piles_take = []
        i = 0
        for p in self.piles:
            if not self.piles_taken[i] and len(p) > 0:
                idx_take.append(i)
                piles_take.append(p)
            i += 1
        return (piles_take,idx_take)

    def get_piles_draw(self):
        """ get the piles which can accept another card

        Returns a tuple (P,I), where P is a list of the available piles, and
        I is a list of indices corresponding to the full list of piles.

        """
        idx_draw = []
        piles_draw = []
        i = 0
        for p in self.piles:
            if not self.two_player:
                if not self.piles_taken[i] and len(p) < 3:
                    idx_draw.append(i)
                    piles_draw.append(p)
            else:
                if len(p) <= i and not self.piles_taken[i]:
                    idx_draw.append(i)
                    piles_draw.append(p)
            i += 1
        return (piles_draw,idx_draw)
        