import {useState, useEffect} from 'react';

interface ManagePortfolioDisplayProps {
    user_id: string;
    user_name: string;
}

export function ManagePortfolioDisplay({user_id, user_name}: ManagePortfolioDisplayProps) {
    // portfolio items are stored as JSON objects 
    // keys are ticker, qantity, price, and purchase_date
    const [portfolio, setPortfolio] = useState<JSON[]>([]);

    return (
    <div>
        <h1>{user_name}'s portfolio</h1>
        <h4>id: {user_id}</h4>
        <div>
            <table>
                <tr>
                    <th>Ticker</th>
                    <th>Quantity</th>
                    <th>Price</th>
                    <th>Purchase Date</th>
                </tr>
                {portfolio.map((item) => (
                    <tr>
                        <td>{item["ticker"]}</td>
                        <td>{item["quantity"]}</td>
                        <td>{item["price"]}</td>
                        <td>{item["purchase_date"]}</td>
                    </tr>
                ))}
            </table>
        </div>
    </div>
    )
}

export default ManagePortfolioDisplay;