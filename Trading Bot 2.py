class JumpingRedElephant(QCAlgorithm):

    def Initialize(self):
        self.SetStartDate(2021, 1, 1)  # Set Start Date
        self.SetEndDate(2021, 1, 5)  # Set Start Date
        self.SetCash(25000)  # Set Strategy Cash
        self.symbol = self.AddEquity("AMD", Resolution.Minute).Symbol
        
        self.Schedule.On(self.DateRules.EveryDay(self.symbol), self.TimeRules.BeforeMarketClose(self.symbol, 10), self.ExitPositions) # exit all positions 15 mins before close
        
        self.volume_one = 0
        self.volume_two = 0

    def OnData(self, data: Slice):

        if self.Time > self.Time.replace(hour=15, minute=39): # don't trade in the last 20 mins of the day
            return
        
        self.volume_one = self.History(self.symbol, 1, Resolution.Minute).volume # get volume of the last minute
        
        # this statement is just used to check if other things are working (works for buing stock)
        if float(self.volume_one) > float(self.volume_two) and float(self.volume_one) != 0 and float(self.volume_two) != 0: 
            self.SetHoldings(self.symbol, 1)
        
        # how to create a plot for testing purposes
        self.Plot("Indicator", "Volume1", self.volume_one)
        self.Plot("Indicator", "Volume2", self.volume_two)
        
        self.volume_two = self.volume_one # sets volume of 2nd minute to volume of first minute before next ondata
    
    
    def ExitPositions(self):
        self.Liquidate(self.symbol) # exit all positions