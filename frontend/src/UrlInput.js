import React, {useState} from 'react';
import axios from 'axios';

const UrlInput = ({setItemData, setError}) => {
    const [url, setUrl] = useState('');

    const handleChange = (event) => {
        setUrl(event.target.value);
    };

    const handleSubmit = () => {
        axios.post("http://localhost:44456/url", {url})
            .then((response) => {
                setItemData(response.data);
                setError('');
            })
            .catch((error) => {
                setError(error.response.data.error);
                setItemData(null);
            });
    };

    return (
        <div className="url-input">
            <input type="text" value={url} onChange={handleChange} placeholder="Enter URL"/>
            <button type="button" onClick={handleSubmit}>Submit URL</button>
        </div>
    );
};

export default UrlInput;
