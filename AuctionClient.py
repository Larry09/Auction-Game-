import socket
import random


class AuctionClient(object):
    """A client for bidding with the AucionRoom"""
    def __init__(self, host="localhost", port=8020, mybidderid=None, verbose=False):
        self.verbose = verbose
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((host,port))
        forbidden_chars = set(""" '".,;:{}[]()""")
        if mybidderid:
            if len(mybidderid) == 0 or any((c in forbidden_chars) for c in mybidderid):
                print("""mybidderid cannot contain spaces or any of the following: '".,;:{}[]()!""")
                raise ValueError
            self.mybidderid = mybidderid
        else:
            self.mybidderid = raw_input("Input team / player name : ").strip()  # this is the only thing that distinguishes the clients
            while len(self.mybidderid) == 0 or any((c in forbidden_chars) for c in self.mybidderid):
              self.mybidderid = raw_input("""You input an empty string or included a space  or one of these '".,;:{}[]() in your name which is not allowed (_ or / are all allowed)\n for example Emil_And_Nischal is okay\nInput team / player name: """).strip()
        self.sock.send(self.mybidderid.encode("utf-8"))

        data = self.sock.recv(5024).decode('utf_8')
        x = data.split(" ")
        if self.verbose:
            print("Have received response of %s" % ' '.join(x))
        if(x[0] != "Not" and len(data) != 0):
          self.numberbidders = int(x[0])
          if self.verbose:
              print("Number of bidders: %d" % self.numberbidders)
          self.numtypes = int(x[1])
          if self.verbose:
              print("Number of types: %d" % self.numtypes)
          self.numitems = int(x[2])
          if self.verbose:
              print("Items in auction: %d" % self.numitems)
          self.maxbudget = int(x[3])
          if self.verbose:
              print("Budget: %d" % self.maxbudget)
          self.neededtowin = int(x[4])
          if self.verbose:
              print("Needed to win: %d" % self.neededtowin)
          self.order_known = "True" == x[5]
          if self.verbose:
              print("Order known: %s" % self.order_known)
          self.auctionlist = []
          self.winnerpays = int(x[6])
          if self.verbose:
              print("Winner pays: %d" % self.winnerpays)
          self.values = {}
          self.artists = {}
          order_start = 7
          if self.neededtowin > 0:
              self.values = None
              for i in range(7, 7+(self.numtypes*2), 2):
                  self.artists[x[i]] = int(x[i+1])
                  order_start += 2
              if self.verbose:
                  print("Item types: %s" % str(self.artists))
          else:
              for i in range(7, 7+(self.numtypes*3), 3):
                  self.artists[x[i]] = int(x[i+1])
                  self.values[x[i]] = int(x[i+2])
                  order_start += 3
              if self.verbose:
                  print("Item types: %s" % str(self.artists))
                  print ("Values: %s" % str(self.values))

          if self.order_known:
              for i in range(order_start, order_start+self.numitems):
                  self.auctionlist.append(x[i])
              if self.verbose:
                  print("Auction order: %s" % str(self.auctionlist))

        self.sock.send('connected '.encode("utf-8"))

        data = self.sock.recv(5024).decode('utf_8')
        x = data.split(" ")
        if x[0] != 'players':
            print("Did not receive list of players!")
            raise IOError
        if len(x) != self.numberbidders + 2:
            print("Length of list of players received does not match numberbidders!")
            raise IOError
        if self.verbose:
         print("List of players: %s" % str(' '.join(x[1:])))

        self.players = []

        for player in range(1, self.numberbidders + 1):
          self.players.append(x[player])

        self.sock.send('ready '.encode("utf-8"))

        self.standings = {name: {artist : 0 for artist in self.artists} for name in self.players}
        for name in self.players:
          self.standings[name]["money"] = self.maxbudget

    def play_auction(self):
        winnerarray = []
        winneramount = []
        done = False
        while not done:
            data = self.sock.recv(5024).decode('utf_8')
            x = data.split(" ")
            if x[0] != "done":
                if x[0] == "selling":
                    currentitem = x[1]
                    if not self.order_known:
                        self.auctionlist.append(currentitem)
                    if self.verbose:
                        print("Item on sale is %s" % currentitem)
                    bid = self.determinebid(self.numberbidders, self.neededtowin, self.artists, self.values, len(winnerarray), self.auctionlist, winnerarray, winneramount, self.mybidderid, self.players, self.standings, self.winnerpays)
                    if self.verbose:
                        print("Bidding: %d" % bid)
                    self.sock.send(str(bid).encode("utf-8"))
                    data = self.sock.recv(5024).decode('utf_8')
                    x = data.split(" ")
                    if x[0] == "draw":
                        winnerarray.append(None)
                        winneramount.append(0)
                    if x[0] == "winner":
                        winnerarray.append(x[1])
                        winneramount.append(int(x[3]))
                        self.standings[x[1]][currentitem] += 1
                        self.standings[x[1]]["money"] -= int(x[3])
            else:
                done = True
                if self.verbose:
                    if self.mybidderid in x[1:-1]:
                        print("I won! Hooray!")
                    else:
                        print("Well, better luck next time...")
        self.sock.close()

    def determinebid(self, numberbidders, wincondition, artists, values, rd, itemsinauction, winnerarray, winneramount, mybidderid, players, standings, winnerpays):
        '''You have all the variables and lists you could need in the arguments of the function,
        these will always be updated and relevant, so all you have to do is use them.
        Write code to make your bot do a lot of smart stuff to beat all the other bots. Good luck,
        and may the games begin!'''

        '''
        numberbidders is an integer displaying the amount of people playing the auction game.

        wincondition is an integer. A postiive integer means that whoever gets that amount of a single type
        of item wins, whilst 0 means each itemtype will have a value and the winner will be whoever accumulates the
        highest total value before all items are auctioned or everyone runs out of funds.

        artists will be a dict of the different item types as keys with the total number of that type on auction as elements.

        values will be a dict of the item types as keys and the type value if wincondition == 0. Else value == None.

        rd is the current round in 0 based indexing.

        itemsinauction is a list where at index "rd" the item in that round is being sold is displayed. Note that it will either be as long as the sum of all the number of the items (as in "artists") in which case the full auction order is pre-announced and known, or len(itemsinauction) == rd+1, in which case it only holds the past and current items, the next item to be auctioned is unknown.

        winnerarray is a list where at index "rd" the winner of the item sold in that round is displayed.

        winneramount is a list where at index "rd" the amount of money paid for the item sold in that round is displayed.

        example: I will now construct a sentence that would be correct if you substituted the outputs of the lists:
        In round 5 winnerarray[4] bought itemsinauction[4] for winneramount[4] pounds/dollars/money unit.

        mybidderid is your name: if you want to reference yourself use that.

        players is a list containing all the names of the current players.

        standings is a set of nested dictionaries (standings is a dictionary that for each person has another dictionary
        associated with them). standings[name][artist] will return how many paintings "artist" the player "name" currently has.
        standings[name]['money'] (remember quotes for string, important!) returns how much money the player "name" has left.

            standings[mybidderid] is the information about you.
            I.e., standings[mybidderid]['money'] is the budget you have left.

        winnerpays is an integer representing which bid the highest bidder pays. If 0, the highest bidder pays their own bid,
        but if 1, the highest bidder instead pays the second highest bid (and if 2 the third highest, ect....). Note though that if you win, you always pay at least 1 (even if the second-highest was 0).

        Don't change any of these values, or you might confuse your bot! Just use them to determine your bid.
        You can also access any of the object variables defined in the constructor (though again don't change these!), or declare your own to save state between determinebid calls if you so wish.

        determinebid should return your bid as an integer. Note that if it exceeds your current budget (standings[mybidderid]['money']), the auction server will simply set it to your current budget.

        Good luck!
        '''

        # Game 1: First to buy wincondition of any artist wins, highest bidder pays own bid, auction order known.
        if (wincondition > 0) and (winnerpays == 0) and self.order_known:
            return self.first_bidding_strategy(numberbidders, wincondition, artists, values, rd, itemsinauction, winnerarray, winneramount, mybidderid, players, standings, winnerpays)

        # Game 2: First to buy wincondition of any artist wins, highest bidder pays own bid, auction order not known.
        if (wincondition > 0) and (winnerpays == 0) and not self.order_known:
            return self.second_bidding_strategy(numberbidders, wincondition, artists, values, rd, itemsinauction, winnerarray, winneramount, mybidderid, players, standings, winnerpays)

        # Game 3: Highest total value wins, highest bidder pays own bid, auction order known.
        if (wincondition == 0) and (winnerpays == 0) and self.order_known:
            return self.third_bidding_strategy(numberbidders, wincondition, artists, values, rd, itemsinauction, winnerarray, winneramount, mybidderid, players, standings, winnerpays)

        # Game 4: Highest total value wins, highest bidder pays second highest bid, auction order known.
        if (wincondition == 0) and (winnerpays == 1) and self.order_known:
            return self.fourth_bidding_strategy(numberbidders, wincondition, artists, values, rd, itemsinauction, winnerarray, winneramount, mybidderid, players, standings, winnerpays)

        # Though you will only be assessed on these four cases, feel free to try your hand at others!
        # Otherwise, this just returns a random bid.
        return self.random_bid(standings[mybidderid]['money'])

    def random_bid(self, budget):
        """Returns a random bid between 1 and left over budget."""
        return int(budget*random.random()+1)

    def first_bidding_strategy(self, numberbidders, wincondition, artists, values, rd, itemsinauction, winnerarray, winneramount, mybidderid, players, standings, winnerpays):
        """Game 1: First to buy wincondition of any artist wins, highest bidder pays own bid, auction order known."""

        # Currently just returns a random bid
        bid = 0
        daV = "Da_Vinci"
        davCounter = 0
        piC = "Picasso"
        piCounter = 0
        vG = "Van_Gogh"
        vGCounter = 0
        rM = "Rembrandt"
        rMCounter = 0
        # Buy any paintings x5 of any artits
        for artistPaintings in itemsinauction:  # Looking at the list auction , estimating if a painting is either a dv, rm , vg, or pi
            # looking at the occurance of the paintings for 5 times bid on that
            if artistPaintings == daV:
                davCounter += 1
                if davCounter == 5 and itemsinauction[rd] == daV:  # if dav == 5
                    bid = 50
                    break
        for artistPaintings in itemsinauction:
            if artistPaintings == piC:  # IF VARIABLE == PICASSO
                piCounter += 1
                if piCounter == 5 and itemsinauction[rd] == piC:  # if COUNTER == 5 and the list has it THEN :
                    bid = 50
                    break
        for artistPaintings in itemsinauction:
            if artistPaintings == vG:
                vGCounter += 1
                if vGCounter == 5 and itemsinauction[rd] == vG:
                    bid = 50
                    break
        for artistPaintings in itemsinauction:
            if artistPaintings == rM:
                rMCounter += 1
                if rMCounter == 5 and itemsinauction[rd] == rM:
                    bid = 50
                    break

        print("LAHIRU strategy 1 Budget left: {}.".format(standings[mybidderid]['money']))
        print("standing is: ", standings)
        print(rd)
        return bid

    def second_bidding_strategy(self, numberbidders, wincondition, artists, values, rd, itemsinauction, winnerarray, winneramount, mybidderid, players, standings, winnerpays):
        """Game 2: First to buy wincondition of any artist wins, highest bidder pays own bid, auction order not known."""

        # Currently just returns a random bid
        bid = 0
        # # Buy any paintings x5 of any artits
        for items in itemsinauction:
            if items == items and standings[mybidderid]['money'] <= 1000:  # Repetitive but, to the point if the item is in that list
                bid = 175  # and my budget < = 1000 THEN bid 175 and so on...
                break
        for items in itemsinauction:
            if items == items and standings[mybidderid]['money'] <= 800:
                bid = 90
                break
        for items in itemsinauction:
            if items == items and standings[mybidderid]['money'] <= 700:
                bid = 100
                break
        for items in itemsinauction:
            if items == items and standings[mybidderid]['money'] <= 500:
                bid = 50
                break
        for items in itemsinauction:
            if items == items and standings[mybidderid]['money'] <= 200:
                bid = 60
                break
        for items in itemsinauction:
            if items == items and standings[mybidderid]['money'] <= 100:
                bid = 50
                break
        for items in itemsinauction:
            if items == items and standings[mybidderid]['money'] <= 50:
                bid = 7
                break
        for items in itemsinauction:
            if items == items and standings[mybidderid]['money'] <= 20:
                bid = 5
                break

        print("LAHIRU strategy 2 Budget left: {}.".format(standings[mybidderid]['money']))
        print(standings)
        print(rd)
        return bid

    def third_bidding_strategy(self, numberbidders, wincondition, artists, values, rd, itemsinauction, winnerarray, winneramount, mybidderid, players, standings, winnerpays):
        """Game 3: Highest total value wins, highest bidder pays own bid, auction order known."""

        # Currently just returns a random bid
        bid = 0
        daV = "Da_Vinci"
        piC = "Picasso"
        vG = "Van_Gogh"
        rM = "Rembrandt"

        # Confusing people in the first rounds, with a high budget, pay aggressive
        # Each var == to the value in the paintigs name , bid on that amount, UNTIL budget == 400,
        # Then use passive to  bid for the rest and switch in between
        for value in values:
            if daV == value and itemsinauction[rd] == daV:  # if the value reprsented in that round == Da_Vinci  bid : this amount of money and so on
                bid = 165
                break
            if piC == value and itemsinauction[rd] == piC:
                bid = 150
                break
            if vG == value and itemsinauction[rd] == vG:
                bid = 130
                break
            if rM == value and itemsinauction[rd] == rM:
                bid = 110
                break

        for cost in values:
            if cost == cost and standings[mybidderid]['money'] <= 400:
                bid = 100
                break
        for costLess1 in values:
            if costLess1 == costLess1 and standings[mybidderid]['money'] <= 300:
                bid = 40
                break
        for costLess2 in values:
            if costLess2 == costLess2 and standings[mybidderid]['money'] <= 200:
                bid = 60
                break
        for costLess02 in values:
            if costLess02 == costLess02 and standings[mybidderid]['money'] <= 150:
                bid = 30
                break
        for costLess3 in values:
            if costLess3 == costLess3 and standings[mybidderid]['money'] <= 100:
                bid = 20
                break
        for costLess4 in values:
            if costLess4 == costLess4 and standings[mybidderid]['money'] <= 50:
                bid = 7
                break
        for costLess8 in values:
            if costLess8 == costLess8 and standings[mybidderid]['money'] <= 20:
                bid = 5
                break
        for costLess5 in values:
            if costLess5 == costLess5 and standings[mybidderid]['money'] <= 7:
                bid = 3
                break
        for costLess6 in values:
            if costLess6 == costLess6 and standings[mybidderid]['money'] <= 5:
                bid = 1
                break
        print("LAHIRU strategy: 3 Budget left: {}.".format(standings[mybidderid]['money']))
        print(standings)
        print(rd)
        return bid

    def fourth_bidding_strategy(self, numberbidders, wincondition, artists, values, rd, itemsinauction, winnerarray, winneramount, mybidderid, players, standings, winnerpays):
        """Game 4: Highest total value wins, highest bidder pays second highest bid, auction order known."""

        bid = 0
        daV = "Da_Vinci"
        piC = "Picasso"
        vG = "Van_Gogh"
        rM = "Rembrandt"
        # Similar option in Game 3, bid aggresive and passive for certain patinings until reaching the value 700 from budget
        # From there see how other players would bid and play from there, with the remaining budget, either go high or go low
        # Easy and quick way to confuse people
        for cost in values:
            if cost == daV and standings[mybidderid]['money'] <= 1000:
                bid = 150
                break
            if cost == piC and standings[mybidderid]['money'] <= 1000:
                bid = 120
                break
            if cost == vG and standings[mybidderid]['money'] <= 1000:
                bid = 150
                break
            if cost == rM and standings[mybidderid]['money'] <= 1000:
                bid = 130
                break

        for budget in itemsinauction:
            if budget == budget and standings[mybidderid]['money'] <= 700:
                bid = 100
                break
        for budget in itemsinauction:
            if budget == budget and standings[mybidderid]['money'] <= 500:
                bid = 80
                break

        for budget in itemsinauction:
            if budget == budget and standings[mybidderid]['money'] <= 300:
                bid = 75
                break
        for budget in itemsinauction:
            if budget == budget and standings[mybidderid]['money'] <= 125:
                bid = 45
                break
        for budget in itemsinauction:
            if budget == budget and standings[mybidderid]['money'] <= 50:
                bid = 25
                break
        for budget in itemsinauction:
            if budget == budget and standings[mybidderid]['money'] <= 20:
                bid = 4
                break
        print("LAHIRU Strategy: 4 Budget left: {}.".format(standings[mybidderid]['money']))
        print(standings)
        return bid
