# self.Securities[contract_symbol].Price returns the mid-price = (bid+ask)/2

class JumpingRedElephant(QCAlgorithm):

    def Initialize(self):
        self.SetStartDate(2022, 5, 11)  # Set Start Date
        self.SetEndDate(2022, 5, 13)  # Set Start Date
        self.SetCash(25000)  # Set Strategy Cash
        
        self.stocks = []
        self.symbols = []
        for ticker in ["AMD", "BBBY"]:
            option = self.AddOption(ticker)
            self.symbols.append(option.Symbol)
            option.SetFilter(-2, 2, timedelta(0), timedelta(8)) # get options contracts within 2 strikes that expire between 0 and 8 days from today
            
            stock = self.AddEquity(ticker, Resolution.Minute).Symbol # also store stock information for price and volume tracking
            self.stocks.append(stock)
        
        self.Schedule.On(self.DateRules.EveryDay(self.symbols[0]), self.TimeRules.BeforeMarketClose(self.symbols[0], 10), self.ExitPositions) # exit all positions 15 mins before close
        
        self.volume_one = [0] * 2 # initialize volume variables
        self.volume_two = [0] * 2

    def OnData(self, data: Slice):

        if self.Time > self.Time.replace(hour=15, minute=39): # don't trade in the last 20 mins of the day
            return
        
        margin = self.Portfolio.MarginRemaining # remaining buying power of account
            
        for i in range(len(self.stocks)): # get the volume for each ticker we are tracking
            try: # added due to an error when information is not received
                self.volume_one[i] = self.History(self.stocks[i], 1, Resolution.Minute).volume # get volume of the last minute
            except:
                self.volume_one[i] = 0 # if error occurs set volume to 0 so so it is not used
            
        for i in range(len(self.symbols)):
            # need to adjust some parts but margin part is working
            if float(self.volume_one[i]) > float(self.volume_two[i]) and float(self.volume_one[i]) != 0 and float(self.volume_two[i]) != 0 \
            and margin > (self.Portfolio.TotalPortfolioValue * 0.05): 
                for kvp in data.OptionChains: # initiate sequence to buy an ATM call
                    if kvp.Key == self.symbols[i]:
                        chains = kvp.Value
                        self.BuyCall(chains)
        
        # how to create a plot for testing purposes
        #self.Plot("Indicator", "Volume1", self.volume_one[0])
        #self.Plot("Indicator", "Volume2", self.volume_two[0])
        
        for i in range(len(self.stocks)):
            self.volume_two[i] = self.volume_one[i] # sets volume of 2nd minute to volume of first minute before next ondata
    
    
    def ExitPositions(self):
        self.Liquidate() # exit all positions
        
    def BuyCall(self, chains): # buy an ATM call (market order need to change to limit)
        expiry = sorted(chains, key = lambda x: x.Expiry, reverse = True)[0].Expiry # get the furthest expiration date (greater than 0, less than 8)
        calls = [i for i in chains if i.Expiry == expiry and i.Right == OptionRight.Call] # filter out only call options
        call_contracts = sorted(calls, key = lambda x: abs(x.Strike - x.UnderlyingLastPrice)) # sort contracts by closest to the money
        
        if len(call_contracts) == 0:
            return
        self.call = call_contracts[0] # contract with closest strike to current price (ATM)
        
        quantity = self.Portfolio.TotalPortfolioValue / self.call.AskPrice 
        quantity = int(0.05 * quantity / 100) # invest 5% of portfolio in option
        self.Buy(self.call.Symbol, quantity) # buy the contract
        
    def SellCall(self, chains):
        self.Liquidate() # temporary until learn how to sell options