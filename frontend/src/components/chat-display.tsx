import { useState } from 'react';
import { Card, CardContent } from '@/components/ui/card';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Textarea } from '@/components/ui/textarea';


export function ChatDisplay() {
    const [chatContent, setChatContent] = useState("")
    const userMessageSubmit = (textAreaValue: string) => {
        console.log("User message submitted")
        // TODO send the message to the server
        // This will involve establishing a websocket connection on load
        // logging in, and sending the message to the server
        // this will end up in a seperate file
        setChatContent(chatContent + "\n" + textAreaValue)
    }

  const handleKeyPress: React.KeyboardEventHandler<HTMLTextAreaElement> = (e) => {
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
        // <div>
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
            )
        }

export default ChatDisplay