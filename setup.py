from setuptools import setup

setup(
    name="pyg",
    version="0.1",
    py_modules=["tool"],
    install_requires=[
        "Click", 
        "networkx", 
        "requests", 
        "tqdm", 
        "lxml",
        "google_api_python_client",
        "beautifulsoup4",
        "PyYAML"],
    entry_points="""
        [console_scripts]
        pyg=ytd:cli
    """
)