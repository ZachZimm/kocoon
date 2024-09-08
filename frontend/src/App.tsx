import { useState, useEffect } from 'react'
import reactLogo from './assets/react.svg'
import viteLogo from '/vite.svg'
import './App.css'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { ScrollArea } from '@/components/ui/scroll-area'
import {
  ResizableHandle,
  ResizablePanel,
  ResizablePanelGroup,
} from "@/components/ui/resizable"
import { CashFlowChartDisplay } from './components/cash-flow-chart-display'
import { BalanceSheetChartDisplay } from './components/balance-sheet-chart-display'
import { IncomeChartDisplay } from './components/income-chart-display'
import { ChatDisplay } from './components/chat-display'
import ModeToggle from './components/ui/mode-toggle'
import { text } from 'stream/consumers'

// TODO:
// FinancialsDisplay
// Add an input for the user to enter a ticker symbol
// Make the symbol variable dynamic, and make it into a parameter for the ChartDisplay components
// Move all of the ChartDisplay components, plus that input into a single component called FinancialsDisplay
// Come up with a better way of selecting the data to display, as there is a of data and creating buttons
//    hard coded keys is not great for this. It was just a quick way to get something on the screen
// Once all of that is working, add the ability to add multiple symbols and display them all at once, normalizing the data if necessary / user wants it

// 
function App() {

  return (
    <div className='h-[90vh] w-[90vw] items-center justify-center'>
      <ResizablePanelGroup direction="vertical"
      className="justify-self-center h-full rounded-lg border">        
        <ResizablePanel defaultSize={4} className='w-full'>
          <div className="flex flex-col flex-1 py-1 px-2">
            <div className='flex-1 justify-end flex'>
              <ModeToggle />
            </div>
          </div>
        </ResizablePanel>
        <ResizableHandle withHandle/>
        <ResizablePanel className='w-full h-full'>
          <ResizablePanelGroup direction="horizontal"
          className="justify-self-center h-full rounded-lg border">

            <ResizablePanel className='w-full'>
              {/* Chat Panel */}
              <ChatDisplay />
          </ResizablePanel>
            <ResizableHandle withHandle/>
            <ResizablePanel defaultSize={67} className='w-full'>
              {/* Secondary panel */}
              <div className="flex flex-col h-full justify-items-center p-6">
                <h2 className='font-semibold justify-self-center pb-4'>Some buttons and charts</h2>
                {/* These buttons don't do anything other than show how convinient shadcn is,
                      especially how they change with the selected theme*/}
                <ScrollArea className='flex-1'>
                  <Button variant="default">Primary</Button>
                  <Button variant="secondary">Secondary</Button>
                  <Button variant="outline">Outline</Button>
                  <Button variant="destructive">Warning</Button>
                  <br />

                  <br />
                  <CashFlowChartDisplay />
                  <IncomeChartDisplay />
                  <BalanceSheetChartDisplay />
                </ ScrollArea>
              </div>
            </ResizablePanel>
          </ResizablePanelGroup>
        </ResizablePanel>
        <ResizableHandle withHandle/>
        <ResizablePanel defaultSize={0} className='w-full'>
          <div className="flex flex-col flex-1 py-1 px-2">
            <span className='font-semibold'>Nothing here yet...</span>
          </div>
        </ResizablePanel>
      </ResizablePanelGroup>

      
    </div>
  )
}

export default App