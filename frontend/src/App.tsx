import { useState } from 'react'
import reactLogo from './assets/react.svg'
import viteLogo from '/vite.svg'
import './App.css'
import { Button } from '@/components/ui/button'

function App() {
  const [count, setCount] = useState(0)

  return (
    <div>
      <h1>Kocoon</h1>
      <Button variant="primary">Primary</Button>
      <Button variant="secondary">Secondary</Button>
      <Button variant="outline">Outline</Button>
    </div>
  )
}

export default App
