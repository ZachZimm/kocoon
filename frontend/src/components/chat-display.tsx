import { useState } from 'react';
import { Card, CardContent } from '@/components/ui/card';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';


export function ChatDisplay() {
    const [badge1Message, setBadge1Message] = useState("Here is an example question!")
    const [badge2Message, setBadge2Message] = useState("And here's another question you can ask!")
    const userMessageSubmit = (textAreaValue: string) => {
        console.log("User message submitted")
        // TODO send the message to the server
        // This will involve establishing a websocket connection on load
        // logging in, and sending the message to the server

        const chatLog = document.getElementById('chatLog');
        const newMessage = document.createElement('Badge');
        newMessage.className = "border p-1 rounded-md bg-secondary";
        newMessage.innerHTML = textAreaValue;
        chatLog?.appendChild(newMessage);

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
        <div className="flex flex-col h-full justify-items-center p-6">
                     
          <Card className="h-[85%] flex-1 flex flex-col pt-4">
            <div className='px-4'>
              <span className="text-lg font-semibold">Chat:</span>
            </div>
            <CardContent className="h-[98%] flex flex-1 flex-grow-0">
              {/* ScrollArea will fill available space */}
              <ScrollArea className='h-full whitespace-pre-wrap'>
                <div id="chatLog" className="gap-2 flex flex-col">
                </div>
              </ScrollArea>
            </CardContent>
          </Card>
          
          {/* Textarea stays at the bottom */}
          <div>
            <div className='py-2'>
              <Badge variant="default" onClick={() => userMessageSubmit(badge1Message)}>{badge1Message}</Badge>
              <Badge variant="default" onClick={() => userMessageSubmit(badge2Message)}>{badge2Message}</Badge>
            </div>
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