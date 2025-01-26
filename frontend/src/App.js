import React, {useState} from 'react';
import './App.css';
import Header from './Header';
import CameraInput from './CameraInput';
import TextInput from './TextInput';
import FileInput from './FileInput';
import UrlInput from './UrlInput';

function App() {
    const [selectedInput, setSelectedInput] = useState('');
    const [itemData, setItemData] = useState(null);
    const [error, setError] = useState('');

    const renderInputComponent = () => {
        switch (selectedInput) {
            case 'camera':
                return <CameraInput setItemData={setItemData} setError={setError}/>;
            case 'text':
                return <TextInput setItemData={setItemData} setError={setError}/>;
            case 'file':
                return <FileInput setItemData={setItemData} setError={setError}/>;
            case 'url':
                return <UrlInput setItemData={setItemData} setError={setError}/>;
            default:
                return null;
        }
    };

    return (
        <div className="App">
            <Header/>
            <main>
                <h1>Upload an Image with Barcode</h1>
                <div className="input-selection">
                    <button onClick={() => setSelectedInput('camera')}>Camera Input</button>
                    <button onClick={() => setSelectedInput('text')}>Text Input</button>
                    <button onClick={() => setSelectedInput('file')}>File Input</button>
                    <button onClick={() => setSelectedInput('url')}>URL Input</button>
                </div>
                {renderInputComponent()}
                {itemData && (
                    <div className="results-section">
                        <h2>Item Information</h2>
                        <p>Item Name: {itemData.item_name}</p>
                        <p>Item Price: {itemData.item_price}</p>
                    </div>
                )}
                {error && (
                    <div className="results-section">
                        <h2>Error</h2>
                        <p>{error}</p>
                    </div>
                )}
                <section id="contact" className="contact-section">
                    <h2>Contact Us</h2>
                    <ul>
                        <li>example: <a href="mailto:example@example.com">example@example.com</a></li>
                        <li>Jason: <a href="mailto:dankj@wit.edu">dankj@wit.edu</a></li>
                        <li>Aliya: <a href="mailto:vagapovaa@wit.edu">vagapovaa@wit.edu</a></li>
                    </ul>
                </section>
            </main>
            <footer>
                <p>&copy; 2025 Wentworth Institute of Technology. All Rights Reserved.</p>
            </footer>
        </div>
    );
}

export default App;
