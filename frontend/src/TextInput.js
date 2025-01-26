import React, {useState} from 'react';
import axios from 'axios';

const TextInput = ({setItemData, setError}) => {
    const [text, setText] = useState('');

    const handleChange = (event) => {
        setText(event.target.value);
    };

    const handleSubmit = () => {
        axios.post("http://localhost:44456/barcode", {barcode_id: text})
            .then((response) => {
                setItemData(response.data);
                setError('');
            })
            .catch((error) => {
                setError(error.response?.data?.error || "An error occurred");
                setItemData(null);
            });
    };

    return (
        <div className="text-input">
            <input type="text" value={text} onChange={handleChange} placeholder="Enter barcode"/>
            <button type="button" onClick={handleSubmit}>Submit Text</button>
        </div>
    );
};

export default TextInput;
