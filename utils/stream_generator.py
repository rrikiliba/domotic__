def stream_generator(stream):
    """
    Wraps the OpenRouter SDK to yield strings 
    instead of objects for st.write_stream
    """
    # Iterate over the SDK event objects
    for event in stream:
        if event.choices:
            content = event.choices[0].delta.content
            if content:
                yield content