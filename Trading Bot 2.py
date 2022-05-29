# self.Securities[contract_symbol].Price returns the mid-price = (bid+ask)/2
# buying OTM contracts: https://www.quantconnect.com/forum/discussion/8148/profit-loss-in-sell-buy-of-put-call-in-option/p1

class JumpingRedElephant(QCAlgorithm):

    def Initialize(self):
        self.SetStartDate(2021, 1, 1)  # Set Start Date
        self.SetEndDate(2022, 1, 1)  # Set Start Date
        self.SetCash(25000)  # Set Strategy Cash
        self.watch_list = ["AMD", "BBBY"]
        
        PORTFOLIO = len(self.watch_list)
        
        self.stocks = []
        self.symbols = []
        self.average_vol = []
        self.volume_one = [0] * PORTFOLIO # initialize volume variables
        self.volume_two = [0] * PORTFOLIO
        self.current_price = [0] * PORTFOLIO
        self.previous_price = [0] * PORTFOLIO
        self.minute_window = RollingWindow[TradeBar](1)
        self.current_high = [0] * PORTFOLIO
        self.current_low = [0] * PORTFOLIO
        self.spread = [0] * PORTFOLIO
        self.total_spread = [0] * PORTFOLIO
        self.spread_inputs = [0] * PORTFOLIO
        self.avg_spread = [0] * PORTFOLIO
        
        for i in range(len(self.watch_list)):
            self.stock_reference = i
            
            option = self.AddOption(self.watch_list[i])
            self.symbols.append(option.Symbol)
            option.SetFilter(-2, 2, timedelta(0), timedelta(8)) # get options contracts within 2 strikes that expire between 0 and 8 days from today
            
            stock = self.AddEquity(self.watch_list[i], Resolution.Minute).Symbol # also store stock information for price and volume tracking
            self.stocks.append(stock)
            
            volume = self.History(stock, 1, Resolution.Daily).volume # get the volume of the previous day
            avg_vol = volume / 390 # get the average for minutely volume
            self.average_vol.append(avg_vol)

        
        self.Schedule.On(self.DateRules.EveryDay(self.symbols[0]), self.TimeRules.BeforeMarketClose(self.symbols[0], 10), self.ExitPositions) # exit all positions 15 mins before close
        self.Schedule.On(self.DateRules.EveryDay(self.symbols[0]), self.TimeRules.At(9, 15), self.ResetData)
        

    def OnData(self, data: Slice):

        if self.Time > self.Time.replace(hour=15, minute=39) or self.Time < self.Time.replace(hour=9, minute=34): # don't trade in the last 20 mins or first 5 of the day
            return
            
        margin = self.Portfolio.MarginRemaining # remaining buying power of account
        
        for i in range(len(self.stocks)): # get the volume for each ticker we are tracking
            try: # avoid error by skipping stock if no data available
            
                try: # added due to an error when information is not received
                    self.volume_one[i] = self.History(self.stocks[i], 1, Resolution.Minute).volume # get volume of the last minute
                except:
                    self.volume_one[i] = 0 # if error occurs set volume to 0 so so it is not used
                
                self.minute_window.Add(data[self.watch_list[i]]) # get data for each stock in watchlist
                self.current_high[i] = self.minute_window[self.minute_window.Count-1].High # get the max price of last minute
                self.current_low[i] = self.minute_window[self.minute_window.Count-1].Low # get the min price of last minute
                self.spread[i] = self.current_high[i] - self.current_low[i] # calculate the spread
                self.total_spread[i] += self.spread[i]
                self.spread_inputs[i] += 1
                
                self.current_price[i] = data[self.watch_list[i]].Price
            except:
                pass
            
        for i in range(len(self.symbols)):
            strat1 = False
            
            # strat1 SOS, high volume, low spread, red candle
            self.avg_spread[i] = float(self.total_spread[i]) / float(self.spread_inputs[i])
            
            if float(self.volume_one[i]) > float(self.average_vol[i] * 1.5) and float(self.spread[i]) < (self.avg_spread[i] * 0.6) and self.current_price[i] < self.previous_price[i] and float(self.current_price[i]) != 0:
                strat1 = True
            
            if strat1 and float(self.volume_one[i]) != 0 and float(self.volume_two[i]) != 0 \
            and margin > (self.Portfolio.TotalPortfolioValue * 0.05): 
                for kvp in data.OptionChains: # initiate sequence to buy an ATM call
                    if kvp.Key == self.symbols[i]:
                        chains = kvp.Value
                        self.BuyCall(chains)
        
        for i in range(len(self.stocks)):
            self.volume_two[i] = self.volume_one[i] # sets volume of 2nd minute to volume of first minute before next ondata
            self.previous_price[i] = self.current_price[i]
            
        # Volume chart
        self.Plot("Average Volume", "Volume", self.volume_one[0])
        self.Plot("Average Volume", "standard", self.average_vol[0])
        self.Plot("Average Volume", "x1.5", (self.average_vol[0] * 1.5))
        
        self.Plot("spread", "current", self.spread[0])
        self.Plot("spread", "avg", self.avg_spread[0])
        self.Plot("spread", "avg * 0.7", (self.avg_spread[0] * 0.7))
        
    def ExitPositions(self):
        self.Liquidate() # exit all positions
        
    # get new volume data from previous day each day
    def ResetData(self):
        self.average_vol = []
        for i in range(len(self.stocks)):
            volume = self.History(self.stocks[i], 1, Resolution.Daily).volume # get the volume of the previous day
            avg_vol = volume / 390 # get the average for minutely volume
            self.average_vol.append(avg_vol)
            

        
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
        
    # THINGS TO ALTER IN BACK TESTS
    # - strat1 change the amount over average volume is required to be considered high volume (currently 50% aka 1.5)