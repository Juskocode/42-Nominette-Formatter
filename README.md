# L01 Recommender Systems Project

This project contains a Jupyter notebook tutorial on Recommender Systems, originally prepared by Inês Gomes (ines.gomes@fe.up.pt) based on Carlos Soares (csoares@fe.up.pt) tutorial.

## Overview

This notebook covers the fundamentals of recommender systems using Python, including:

- **Dataset Exploration**: Working with the MovieLens 100k dataset
- **User-Item Matrix Creation**: Using both Pandas and Surprise library approaches
- **Recommender System Algorithms**:
  - Popularity-based recommendations
  - Collaborative filtering models
  - Matrix factorization techniques (SVD)
  - K-Nearest Neighbors approaches

## Libraries Used

- **Surprise**: For rating-based interactions (https://surpriselib.com/)
- **Implicit**: For implicit feedback interactions (https://github.com/benfred/implicit/tree/main)
- **LightFM**: For hybrid implementations (https://making.lyst.com/lightfm/docs/index.html#)
- **Pandas**: For data manipulation and analysis
- **NumPy**: For numerical computations
- **Matplotlib**: For data visualization

## Requirements

- Python 3.12 environment
- See `requirements.txt` for detailed package dependencies

## Getting Started

1. Install the required packages: `pip install -r requirements.txt`
2. Launch Jupyter Notebook: `jupyter notebook`
3. Open `L01-recsys.ipynb 2` and start exploring!

## Dataset

The notebook uses the MovieLens 100k dataset, which is automatically downloaded through the Surprise library.

## Additional Resources

- [Kaggle Recommender Systems Tutorial](https://www.kaggle.com/code/gspmoreira/recommender-systems-in-python-101)
- [Jester Dataset](https://eigentaste.berkeley.edu/dataset/)

## Notes

- Surprise library may not work properly with standard pip install - consider using conda or alternative installation methods if you encounter issues.# 42-Nominette-Formatter
