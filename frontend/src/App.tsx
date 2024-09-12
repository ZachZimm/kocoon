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

function App() {
  return (
    <div className='h-[92vh] w-[93vw] items-center justify-center'>
      <ResizablePanelGroup direction="vertical"
      className="justify-self-center h-full rounded-lg border">        
        <ResizablePanel defaultSize={6} className='w-full'>

          {/* Header 
                This will eventually go into a seperate component*/}
          <div className="flex flex-row flex-1 py-1 px-2">
            <h2 className='font-semibold text-lg justify-self-center pb-4'>Kocoon</h2>
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
            <ResizablePanel defaultSize={60} className='w-full'>
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