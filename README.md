# portfolio-tracker
A full-stack web application for real-time tracking and analysis of financial assets

## Demo

https://github.com/user-attachments/assets/bb6333b5-940d-4caf-bd65-9a23800e7f5c

### Built With

* [![Flask][Flask-icon]][Flask-url]
* [![Python][Python-icon]][Python-url]
* [![JS][JS-icon]][JS-url]
* ![HTML][HTML-icon]
* ![CSS][CSS-icon]
* [![Bootstrap][Bootstrap.com]][Bootstrap-url]



<!-- GETTING STARTED -->
## Getting Started

1. Clone the repository
   ```sh
   git clone https://github.com/BorilBalchev/portfolio-tracker.git
   ```
2. Navigate to the repository
   ```sh
   cd portfolio-tracker
   ```
3. Install necessary Python libraries
   ```sh
   pip install -r requirements.txt
   ```
4. Navigate to the `website` subdirectory
   ```sh
   cd website
   ```
5. Create a `.env` file and populate it with a secret key (required to keep the client-side sessions secure, the key can be a random long string)
   ```env
   secret_key=your_secret_key
   ```
6. Navigate back to the `portfolio-tracker` repository and Run the app
   ```sh
   python main.py
   ```
   or for macOS
   ```sh
   python3 main.py
   ```



<!-- USAGE EXAMPLES -->
## Usage

1. Access your account by logging in via the Login page, or create a new account using the Sign Up page.
2. Once logged in, navigate to the Portfolio page to add assets to your portfolio.
3. Easily update the quantity of any asset by clicking on the corresponding number in the portfolio table.
4. The total value of your portfolio is prominently displayed in the upper right corner of the Portfolio page.
5. Conduct in-depth technical analysis and monitor price action for the assets in your portfolio on the Technical Analysis page.
6. Choose from a comprehensive range of technical indicators, including moving averages (SMA, EMA, VWMA) and oscillators (RSI, MACD, ADX, CCI), to enhance your analysis.



<!-- ROADMAP -->
## Roadmap

- [x] Implemented secure login and sign-up processes by hashing passwords and enforcing strong password requirements.
- [x] Enabled real-time tracking of selected digital assets using the yfinance Python library, with data retrieval and updates every 15 seconds.
- [x] Integrated advanced charting capabilities for selected assets using the `Bokeh` Python library, enabling technical analysis with indicators from the `pandas-ta` library, such as moving averages (SMA, EMA, VWMA) and oscillators (RSI, MACD, ADX, CCI).
- [ ] Planned feature: Retrieve the latest news for each asset in the portfolio, creating a personalized news feed for the user.



<!-- CONTRIBUTING -->
## Contributing

Contributions are what make the open source community such an amazing place to learn, inspire, and create. Any contributions you make are **greatly appreciated**.



<!-- LICENSE -->
## License

Distributed under the MIT License. See `LICENSE` for more information.



<!-- CONTACT -->
## Contact

LinkedIn: https://linkedin.com/in/boril-balchev


<!-- Links -->
[Flask-icon]: https://img.shields.io/badge/flask-%23000.svg?style=for-the-badge&logo=flask&logoColor=white
[Flask-url]: https://flask.palletsprojects.com/en/3.0.x/
[Python-icon]: https://img.shields.io/badge/python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54
[Python-url]: https://www.python.org
[JS-icon]: https://img.shields.io/badge/javascript-%23323330.svg?style=for-the-badge&logo=javascript&logoColor=%23F7DF1E
[JS-url]: https://www.oracle.com/developer/javascript/
[HTML-icon]: https://img.shields.io/badge/html5-%23E34F26.svg?style=for-the-badge&logo=html5&logoColor=white
[CSS-icon]: https://img.shields.io/badge/css3-%231572B6.svg?style=for-the-badge&logo=css3&logoColor=white
[Bootstrap.com]: https://img.shields.io/badge/Bootstrap-563D7C?style=for-the-badge&logo=bootstrap&logoColor=white
[Bootstrap-url]: https://getbootstrap.com
