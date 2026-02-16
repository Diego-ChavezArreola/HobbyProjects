from setuptools import setup, find_packages

setup(
    name='super_ani',
    version='0.1.0',
    packages=find_packages(),
    entry_points={
        'console_scripts': [
            'super_ani=super_ani.main:main',  
        ],
    },
    install_requires=[
        
    ],
    python_requires='>=3.6',
)
