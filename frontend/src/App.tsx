import { useState, useEffect } from 'react'
import reactLogo from './assets/react.svg'
import viteLogo from '/vite.svg'
import './App.css'
import {
  ResizableHandle,
  ResizablePanel,
  ResizablePanelGroup,
} from "@/components/ui/resizable"
import { ChatDisplay } from './components/chat-display'
import { FinancialsDisplay } from './components/financials-display'
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
  // const [symbol, setSymbol] = useState('AAPL')

  // const handleSymbolChange = () => {
  //   const tickerInput = document.getElementById('tickerInput') as HTMLInputElement
  //   setSymbol(tickerInput.value)
  //   console.log(tickerInput.value)
  //   tickerInput.value = ''
  // }

  // const handleKeyPress: React.KeyboardEventHandler<HTMLInputElement> = (e) => {
  //   if (e.key === "Enter") {
  //     e.preventDefault(); // Prevents the default newline insertion behavior
  //     handleSymbolChange()
  //   }
  // }

  return (
    <div className='h-[90vh] w-[90vw] items-center justify-center'>
      <ResizablePanelGroup direction="vertical"
      className="justify-self-center h-full rounded-lg border">        
        <ResizablePanel defaultSize={4} className='w-full'>

          {/* Header 
                This will eventually go into a seperate component*/}
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
              <FinancialsDisplay />

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