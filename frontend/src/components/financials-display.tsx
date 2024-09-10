import React, { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { ScrollArea } from '@/components/ui/scroll-area'
import { CashFlowChartDisplay } from './cash-flow-chart-display'
import { IncomeChartDisplay } from './income-chart-display'
import { BalanceSheetChartDisplay } from './balance-sheet-chart-display'

// TODO:
// Let the user specify a start date for data
//      end date would be good too, but is less imprtant
// Come up with a better way of selecting the data to display, as there is a of data and creating buttons
//    hard coded keys is not great for this. It was just a quick way to get something on the screen
// Once that is working, add the ability to add multiple symbols and display them all at once, normalizing the data if necessary / user wants it
// We should also display the stock price history for the selected symbol


export function FinancialsDisplay() {
  const [symbol, setSymbol] = useState('AAPL')

  const handleSymbolChange = () => {
    const tickerInput = document.getElementById('tickerInput') as HTMLInputElement
    setSymbol(tickerInput.value)
    console.log(tickerInput.value)
    tickerInput.value = ''
  }

  const handleKeyPress: React.KeyboardEventHandler<HTMLInputElement> = (e) => {
    if (e.key === "Enter") {
      e.preventDefault(); // Prevents the default newline insertion behavior
      handleSymbolChange()
    }
  }
return (
        <div className="flex flex-col h-full justify-items-center p-3 bg-accent">
            <h2 className='font-semibold justify-self-center pb-2 text-accent-foreground'>Some buttons and charts</h2>
            <ScrollArea className='flex-1'>
                <div className='flex'>
                    <Input placeholder="enter a ticker..." 
                    id='tickerInput' 
                    className='w-[8rem]' 
                    type='text'
                    onKeyDown={handleKeyPress}/>

                    <Button variant="default" onMouseUp={handleSymbolChange}>Submit</Button>

                </div>
                <CashFlowChartDisplay initialSymbol={symbol}/>
                <IncomeChartDisplay initialSymbol={symbol}/>
                <BalanceSheetChartDisplay initialSymbol={symbol}/>

                {/* These buttons don't do anything other than show how convinient shadcn is,
                    especially how they change with the selected theme*/}
                <br/>
                <Button variant="default">Primary</Button>
                <Button variant="secondary">Secondary</Button>
                <Button variant="outline">Outline</Button>
                <Button variant="destructive">Warning</Button>
            </ ScrollArea>
        </div>
    )
}
export default FinancialsDisplay