import setuptools

# with open('README.md', 'r', encoding='utf-8') as fh:
#     long_description = fh.read()


setuptools.setup(
    name='tradetools',  # Replace with your own username
    version='0.0.1',
    # author = 'Example Author',
    # author_email = 'author@example.com',
    # description = 'A small example package',
    # long_description=long_description,
    # long_description_content_type='text/markdown',
    # url='https://github.com/pypa/sampleproject',
    packages=setuptools.find_packages(),
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
    python_requires='>=3.8',
    install_requires=[
        'numpy==1.19.5',
        'pandas',
        'TA-Lib',
        'backtrader',
        'pytest',
        'pytest_cases',
        'tables',
        'pybind11>=2.6.2',

    ]
)
