import { useState, useEffect } from 'react';
import { Card, CardContent } from '@/components/ui/card';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';


export function ChatDisplay() {
    const [badge1Message, setBadge1Message] = useState("Here is an example question!")
    const [badge2Message, setBadge2Message] = useState("And here's another question you can ask!")
    const [socket, setSocket] = useState<WebSocket | null>(null);
    const [lastMessageId, setLastMessageId] = useState<number>(0);

    useEffect(() => {
        // Create WebSocket connection.
        const ws = new WebSocket('wss://host.zzimm.com/ws');

        // Connection opened
        ws.addEventListener('open', () => {
            console.log('WebSocket connection established.');
            userLogin("test_user", ws);
        });

        // Listen for messages
        ws.addEventListener('message', (event) => {
            console.log('Message from server ', event.data);
            // You can also append the message to the chat log here if needed
            const message = JSON.parse(event.data);
            if (message.mode.includes("chat streaming")) {
                if (message.mode.includes("finished")) {
                    setLastMessageId(lastMessageId + 1);
                }
                else {
                    streamResponseMessage(message.message);
                }
            }
        });
        // Save the WebSocket instance to state
        setSocket(ws);
        // Cleanup on component unmount
        return () => {
            ws.close();
        };
      }, []);

    const userLogin = (username: string, _socket: WebSocket) => {
        if (_socket && _socket.readyState === WebSocket.OPEN) {
          // Send the login message to the server
          const loginMessage = JSON.stringify({"func": "login", "username": username});
          _socket.send(loginMessage);
          console.log('Login message sent to server: ', loginMessage);
        } else {
            console.error('WebSocket connection is not open.');
        }
    }

    const streamResponseMessage = (response: string) => {
        const chatLog = document.getElementById('chatLog');
        // check if the latest message's id is the same as the lastMessageId
        // if it is, then append the message to the existing message
        // otherwise, create a new message element
        // with the lastMessageId
        if (chatLog?.lastChild?.id === `message-${lastMessageId}`) {
            const lastMessage = chatLog.lastChild as HTMLElement;
            lastMessage.innerHTML += response;
        }
        else {
            const newMessage = document.createElement('Badge');
            newMessage.className = "border p-1 rounded-md bg-primary text-sm";
            newMessage.innerHTML = response;
            newMessage.id = `message-${lastMessageId}`;
            chatLog?.appendChild(newMessage);
        }
    }

    const userMessageSubmit = (textAreaValue: string) => {
        if (socket && socket.readyState === WebSocket.OPEN) {
          // Send the message to the server
          let message = JSON.stringify({"func": "chat", "message": textAreaValue});
          socket.send(message);
          console.log('Message sent to server: ', message);
        } else {
            console.error('WebSocket connection is not open.');
        }

        const chatLog = document.getElementById('chatLog');
        const newMessage = document.createElement('Badge');
        newMessage.className = "border p-1 rounded-md bg-secondary text-sm";
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
        <div className="flex flex-col h-full justify-items-center p-2">
                     
          <Card className="h-[85%] flex-1 flex flex-col pt-2">
            <div className='px-2'>
              <span className="text-lg font-semibold">Chat:</span>
            </div>
            <CardContent className="h-[98%] w-full flex flex-1 flex-grow-0">
              {/* ScrollArea will fill available space */}
              <ScrollArea className='h-full whitespace-pre-wrap'>
                <div id="chatLog" className="gap-1 flex flex-col">
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