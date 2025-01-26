import React, {useState} from 'react';
import axios from 'axios';

const FileInput = ({setItemData, setError}) => {
    const [file, setFile] = useState(null);

    const handleChange = (event) => {
        setFile(event.target.files[0]);
    };

    const handleSubmit = () => {
        const formData = new FormData();
        formData.append("file", file);

        axios.post("http://localhost:44456/upload", formData)
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
        <div className="file-input">
            <input type="file" onChange={handleChange}/>
            <button type="button" onClick={handleSubmit}>Submit File</button>
        </div>
    );
};

export default FileInput;
