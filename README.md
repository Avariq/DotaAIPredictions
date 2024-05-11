# DotaAIPredictions
National University of Lviv Polytechnic - Bachelor's degreefinal work.

## Init the Project
First off, make sure to build your virtual environment containing all dependencies listed in [requirements file](https://github.com/Avariq/DotaAIPredictions/blob/0f2237fa1a7b28ce98e1f7e1e3885a6b16b52080/requirements.txt)
Afterwards, activate that environment (e.g. venv/Scripts/activate) to make sure your system Python interpreter remains intact.


## Predictions
### Mandatory files
In order to predict the match outcome, please head to the [predictor/](https://github.com/Avariq/DotaAIPredictions/tree/0f2237fa1a7b28ce98e1f7e1e3885a6b16b52080/predictor) dir.
<br>The [DotaMatchResultPredictor.py](https://github.com/Avariq/DotaAIPredictions/blob/0f2237fa1a7b28ce98e1f7e1e3885a6b16b52080/predictor/DotaMatchResultPredictor.py) is the core of the system which requires [RandomForest](https://github.com/Avariq/DotaAIPredictions/blob/0f2237fa1a7b28ce98e1f7e1e3885a6b16b52080/predictor/random_forest_model.joblib) and [LogisticRergression](https://github.com/Avariq/DotaAIPredictions/blob/0f2237fa1a7b28ce98e1f7e1e3885a6b16b52080/predictor/logistic_regression_model.joblib) model files, [csv snapshot of heroes table](https://github.com/Avariq/DotaAIPredictions/blob/0f2237fa1a7b28ce98e1f7e1e3885a6b16b52080/predictor/heroes_table.csv) as well as the [json config file](https://github.com/Avariq/DotaAIPredictions/blob/0f2237fa1a7b28ce98e1f7e1e3885a6b16b52080/predictor/predictor_config.json) to be present in the same directory for it to work properly.

### Config file
In the predictor's config file you will notice two lines: [filepath](https://github.com/Avariq/DotaAIPredictions/blob/0f2237fa1a7b28ce98e1f7e1e3885a6b16b52080/predictor/predictor_config.json#L2) and [enable_debug](https://github.com/Avariq/DotaAIPredictions/blob/0f2237fa1a7b28ce98e1f7e1e3885a6b16b52080/predictor/predictor_config.json#L3).
<br>First one is mandatory as it points the predictor to its input while second is of use for debugging purposes and may remain as is.

### System's Input
The [filepath](https://github.com/Avariq/DotaAIPredictions/blob/0f2237fa1a7b28ce98e1f7e1e3885a6b16b52080/predictor/predictor_config.json#L2) property should lead to a json file containing the information about all 10 players of the match. Use [input_sample.json](https://github.com/Avariq/DotaAIPredictions/blob/0f2237fa1a7b28ce98e1f7e1e3885a6b16b52080/predictor/input_sample.json) and [input_sample2.json](https://github.com/Avariq/DotaAIPredictions/blob/0f2237fa1a7b28ce98e1f7e1e3885a6b16b52080/predictor/input_sample2.json) for reference.

<b>NOTE: The file MUST contain all the data for all the players

### Using the system
After the configuration and input are ready, run the [DotaMatchResultPredictor.py](https://github.com/Avariq/DotaAIPredictions/blob/0f2237fa1a7b28ce98e1f7e1e3885a6b16b52080/predictor/DotaMatchResultPredictor.py) via Python.

<br>Or build it using `pyinstaller -F predictor/DotaMatchResultPredictor.py` to get the executable and run it manually.

### Example #1 ([input_sample.json](https://github.com/Avariq/DotaAIPredictions/blob/0f2237fa1a7b28ce98e1f7e1e3885a6b16b52080/predictor/input_sample.json))
<img src="https://github.com/Avariq/DotaAIPredictions/assets/48154142/29db0d1d-d00b-4863-a2e1-e6ebd7720fbf" width=400 height=500>

### Example #2 ([input_sample2.json](https://github.com/Avariq/DotaAIPredictions/blob/0f2237fa1a7b28ce98e1f7e1e3885a6b16b52080/predictor/input_sample2.json))
<img src="https://github.com/Avariq/DotaAIPredictions/assets/48154142/4ff32a85-10f3-43b5-b2c5-5eef7e894c77" width=400 height=500>
