import { useState, useEffect } from 'react'
import reactLogo from './assets/react.svg'
import viteLogo from '/vite.svg'
import './App.css'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { Input } from '@/components/ui/input'
import { ScrollArea } from '@/components/ui/scroll-area'
import {
  ResizableHandle,
  ResizablePanel,
  ResizablePanelGroup,
} from "@/components/ui/resizable"
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { text } from 'stream/consumers'
import ModeToggle from './components/ui/mode-toggle'

function App() {
  const [chatContent, setChatContent] = useState("")

  const userMessageSubmit = (textAreaValue) => {
    console.log("User message submitted")
    // TODO send the message to the server
    // This will involve establishing a websocket connection
    // and sending the message to the server
    setChatContent(chatContent + "\n" + textAreaValue)
  }

  const handleKeyPress = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault(); // Prevents the default newline insertion behavior
      const textAreaValue = e.target.value;
      if (textAreaValue.trim() !== "") {
        userMessageSubmit(textAreaValue);
      }
      e.target.value = "";
    }
  }

  return (
    <div className='h-[90vh] w-[90vw] items-center justify-center'>

      <ResizablePanelGroup direction="horizontal"
      className="justify-self-center h-full rounded-lg border">
        <ResizablePanel className='w-full'>
          {/*Chat Panel
              This should probably be in a seperate component / file*/}
          <div className="flex flex-col h-full justify-items-center p-6">
            <h1 className='font-semibold justify-self-center pb-4'>Kocoon</h1>         
            <Card className="flex-1 flex flex-col pt-4">
            <div className='px-4'>
              <span className="text-lg font-semibold">Chat:</span>
            </div>
            <CardContent className="flex-1 overflow-hidden">
              {/* ScrollArea will fill available space */}
              <ScrollArea className='flex-1 whitespace-pre-wrap'>
                {chatContent}
              </ScrollArea>
            </CardContent>
          </Card>
          
          {/* Textarea stays at the bottom */}
          <div className='pt-4'>
            <Textarea 
              id="userMessageTextArea"
              placeholder="Type your message here..."
              onKeyUp={handleKeyPress}
            />
          </div>
        </div>
      </ResizablePanel>
        <ResizableHandle withHandle/>
        <ResizablePanel defaultSize={50} className='w-full'>
          { /* Secondary panel
                This will probably contain charts or something,
                but it will likely end up in a seperate component too */ }
          <div className='flex-auto w-full h-full items-center justify-center p-6'>
            <h1 className='font-semibold justify-self-center pb-4'>Some Buttons</h1>
            {/* These buttons just show how convinient shadcn is,
                  especially how they change with the selected theme*/}
            <Button variant="default">Primary</Button>
            <Button variant="secondary">Secondary</Button>
            <Button variant="outline">Outline</Button>
            <Button variant="destructive">Warning</Button>
            <br />
            <ModeToggle />
          </div>
          
        </ResizablePanel>
        
      </ResizablePanelGroup>
    </div>
    
  )
}

export default App
