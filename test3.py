import os, sys, json
import numpy as np
import matplotlib.pyplot as plt
import matplotlib as mpl
import math
from matplotlib.ticker import FormatStrFormatter, MultipleLocator

ALL_DATASETS = ['midv500', 'midv2019', 'ic15', 'yvt']
ESTIMATION_PLOT_DATASETS = [['midv500', 'midv2019'], ['ic15', 'yvt']]
TIMING_PLOT_DATASETS = [['midv500', 'midv2019'], ['ic15', 'yvt']]

EPPS_DATASETS = ['midv500', 'midv2019']
#EPPS_DATASETS = ['midv500']
#EPPS_DATASETS = ['ic15', 'yvt']

EPPS_YLIMITS = {
    'midv500': [0.06, 0.125],
    'midv2019': [0.09, 0.25],
    'ic15': [0.15, 0.35],
    'yvt': [0.195, 0.24]
}

DATASET_LABELS = {
    'midv500': 'MIDV-500',
    'midv2019': 'MIDV-2019',
    'ic15': 'IC15-Train',
    'yvt': 'YVT'
}

METHODS = ['summation', 'treap', 'base']
#METHODS = ['summation']

PRECALC_DIRECTORIES = {}
for dataset in ALL_DATASETS:
    PRECALC_DIRECTORIES[dataset] = {
        'base': './precalc_base_%s' % dataset,
        'summation': './precalc_summation_%s' % dataset,
        'treap': './precalc_treap_%s' % dataset
    }
    
PRECALC_DISTANCE_DIRECTORIES = {}
for dataset in ALL_DATASETS:
    PRECALC_DISTANCE_DIRECTORIES[dataset] = {
        'base': './precalc_distance_base_%s' % dataset,
        'summation': './precalc_distance_summation_%s' % dataset,
        'treap': './precalc_distance_treap_%s' % dataset
    }

PLOT_COLOR = { 'base': '0.0', 'summation': '0.5', 'treap': '0.2' }
PLOT_LINESTYLE = { 'base': '-', 'summation': '--', 'treap': ':' }
PLOT_MARKER = { 'base': None, 'summation': 'o', 'treap': None }
PLOT_MARKERSIZE = { 'base': None, 'summation': 6, 'treap': None }
PLOT_LINEWIDTH = { 'base': 1.5, 'summation': 1.5, 'treap': 2.0 }

PLOT_LABEL = {
    'base': 'Base method', 
    'summation': 'Method A',
    'treap': 'Method B'
}

def SES(time_series, smoothing_coeficient):
    s = np.zeros(len(time_series)+1)
    s[0] = time_series[0]
    for i in range(1, len(time_series)):
        s[i] = s[i-1] + smoothing_coeficient * (time_series[i] - s[i-1])
    s[len(time_series)] = s[len(time_series)-1] + smoothing_coeficient * (time_series[-1] - s[len(time_series)-1])
    return s

def LSM_AR(time_series):
    x = np.arange(1, len(time_series)+1, 1)
    #first row
    a_11 = 2*len(time_series)
    a_12 = 0
    a_21 = 0
    a_22 = 0
    b_1 = 0
    b_2 = 0    
    for i in range(len(x)):
        a_12 += x[i]
        a_21 += x[i]
        a_22 += x[i] * x[i]
        b_1 += time_series[i]
        b_2 += time_series[i] * x[i]        
    a_12 *= 2
    a_22 *= 2
    b_1 *= 2
    b_2 *= 2
    a = np.array([[a_11, a_12], [a_21, a_22]])
    b = np.array([b_1, b_2])
    sltn = np.linalg.solve(a, b)
    return sltn[0] + sltn[1] * (x[-1] + 1) 

def LSM_SQR(time_series):
    x = np.arange(1, len(time_series)+1, 1)
    frac_top = 0
    frac_bottom = 0
    for i in range(len(x)):  
        frac_top += time_series[i] * (x[i] ** 2)
        frac_bottom += x[i]**4
    b = frac_top/frac_bottom
    return b*(x[-1] + 1)

def MA(time_series):
    res = 0
    for i in range (len(time_series)):
        res += time_series[i]
    res /= len(time_series)
    return res

def lin_LSE(x, y, coef):
    if len(x) == 1:
        return [0, y[0]]
    x_e = []
    for i in range(len(x)):
        x_e.append(math.e**(x[i] * coef))
    sum_x = 0
    sum_x2 = 0
    sum_y = 0
    sum_xy = 0
    for i in range(len(x_e)):
        sum_x += x_e[i]
        sum_x2 += x_e[i]**2
        sum_y += y[i]
        sum_xy += x_e[i] * y[i]
    det = sum_x2 * len(x_e) - sum_x * sum_x
    det_1 =  -1 * (sum_x * sum_y - sum_xy * len(x_e))
    det_2 = sum_x2 * sum_y - sum_xy * sum_x
    return [det_1/det, det_2/det]


def F(a, b, c, x, y):
    res = 0
    for i in range(len(x)):
        res += (a * math.e**(b*x[i]) + c - y[i])**2
    return res

def trenar_search_exp(f, x, y, x_L, x_R):
    eps = 1e-6
    left_ = x_L
    right_ = x_R
    while right_ > left_+eps:
        t = (right_ - left_)/3
        a = left_ + t
        b = right_ - t
        a_coefs = lin_LSE(x, y, a)
        b_coefs = lin_LSE(x, y, b)
        if f(a_coefs[0], a, a_coefs[1], x, y) < f(b_coefs[0], b, b_coefs[1], x, y):
            right_ = b
        else:
            left_ = a
    fin_k, fin_c = lin_LSE(x, y, (left_+right_)/2) 
    return [(left_+right_)/2, fin_k, fin_c]
    
def LSM_exp(time_series, window):
    #window_ = window
    #if window > len(time_series):
    #    window_ = len(time_series)    
    #time_series_ = time_series[-1*window_:]
    time_series_ = time_series
    x = []
    for i in range(len(time_series_)):
        x.append(i+1)
    fin_coefs = trenar_search_exp(F, x, time_series_, -10, 10)
    return fin_coefs[1] * (math.e**(fin_coefs[0] * (x[-1]+1))) + fin_coefs[2]

def roc_curve_LSM_SQR_stoppers(method, dataset):
    precalc_dir = PRECALC_DIRECTORIES[dataset][method]
    precalc_dist_dir = PRECALC_DISTANCE_DIRECTORIES[dataset][method]
    x = []
    y = []
    
    precalc = []
    precalc_dist = []
    precalc_dist_files = [os.path.join(precalc_dist_dir, x) for x in os.listdir(precalc_dist_dir)]
    precalc_files = [os.path.join(precalc_dir, x) for x in os.listdir(precalc_dir)]
    for precalc_file in precalc_files:
        precalc_data = None
        with open(precalc_file) as js:
            precalc_data = json.load(js)
        precalc.append(precalc_data)
    for precalc_dist_file in precalc_dist_files:
        precalc_dist_data = None
        if precalc_dist_file.endswith('.json'):
            with open(precalc_dist_file) as js:
                precalc_dist_data = json.load(js)
                precalc_dist.append(precalc_dist_data)
              
    points_of_interest = []
    for i in range (len(precalc)):
        points_of_interest.append([i, 0, precalc_dist[i][0], precalc[i][0][0]])
        for j in range(1, len(precalc[i])):
            if LSM_SQR(precalc_dist[i][0:j]) < points_of_interest[-1][2]:
                points_of_interest.append([i, j, LSM_SQR(precalc_dist[i][0:j]), precalc[i][j][0]])
    
    
    points_of_interest = sorted(points_of_interest, key = lambda POI: POI[2], reverse = True)
    stopping_frames_id = [0 for i in range(len(precalc))]
    sum_of_frames = len(precalc)
    sum_of_errors = 0
    for i in range(len(precalc)):
        sum_of_errors += precalc[i][0][0]
    
    x.append(sum_of_frames/len(precalc))
    y.append(sum_of_errors/len(precalc))
    for i in range(len(points_of_interest)):
        sum_of_frames -= (stopping_frames_id[points_of_interest[i][0]]+1)
        sum_of_errors -= precalc[points_of_interest[i][0]][stopping_frames_id[points_of_interest[i][0]]][0]
        stopping_frames_id[points_of_interest[i][0]] = points_of_interest[i][1]
        sum_of_frames += (points_of_interest[i][1]+1)
        sum_of_errors += points_of_interest[i][3]
        x.append(sum_of_frames/len(precalc))
        y.append(sum_of_errors/len(precalc))     
    return x, y


def roc_curve_LSM_AR_stoppers(method, dataset):
    precalc_dir = PRECALC_DIRECTORIES[dataset][method]
    precalc_dist_dir = PRECALC_DISTANCE_DIRECTORIES[dataset][method]
    x = []
    y = []
    
    precalc = []
    precalc_dist = []
    precalc_dist_files = [os.path.join(precalc_dist_dir, x) for x in os.listdir(precalc_dist_dir)]
    precalc_files = [os.path.join(precalc_dir, x) for x in os.listdir(precalc_dir)]
    for precalc_file in precalc_files:
        precalc_data = None
        with open(precalc_file) as js:
            precalc_data = json.load(js)
        precalc.append(precalc_data)
    for precalc_dist_file in precalc_dist_files:
        precalc_dist_data = None
        if precalc_dist_file.endswith('.json'):
            with open(precalc_dist_file) as js:
                precalc_dist_data = json.load(js)
                precalc_dist.append(precalc_dist_data)
              
    points_of_interest = []
    for i in range (len(precalc)):
        points_of_interest.append([i, 0, precalc_dist[i][0], precalc[i][0][0]])
        for j in range(1, len(precalc[i])):
            if LSM_AR(precalc_dist[i][0:j]) < points_of_interest[-1][2]:
                points_of_interest.append([i, j, LSM_AR(precalc_dist[i][0:j]), precalc[i][j][0]])
    
    
    points_of_interest = sorted(points_of_interest, key = lambda POI: POI[2], reverse = True)
    stopping_frames_id = [0 for i in range(len(precalc))]
    sum_of_frames = len(precalc)
    sum_of_errors = 0
    for i in range(len(precalc)):
        sum_of_errors += precalc[i][0][0]
    
    x.append(sum_of_frames/len(precalc))
    y.append(sum_of_errors/len(precalc))
    for i in range(len(points_of_interest)):
        sum_of_frames -= (stopping_frames_id[points_of_interest[i][0]]+1)
        sum_of_errors -= precalc[points_of_interest[i][0]][stopping_frames_id[points_of_interest[i][0]]][0]
        stopping_frames_id[points_of_interest[i][0]] = points_of_interest[i][1]
        sum_of_frames += (points_of_interest[i][1]+1)
        sum_of_errors += points_of_interest[i][3]
        x.append(sum_of_frames/len(precalc))
        y.append(sum_of_errors/len(precalc))    
    return x, y


def roc_curve_LSM_exp_stoppers(method, dataset):
    precalc_dir = PRECALC_DIRECTORIES[dataset][method]
    precalc_dist_dir = PRECALC_DISTANCE_DIRECTORIES[dataset][method]
    x = []
    y = []
    
    precalc = []
    precalc_dist = []
    precalc_dist_files = [os.path.join(precalc_dist_dir, x) for x in os.listdir(precalc_dist_dir)]
    precalc_files = [os.path.join(precalc_dir, x) for x in os.listdir(precalc_dir)]
    for precalc_file in precalc_files:
        precalc_data = None
        with open(precalc_file) as js:
            precalc_data = json.load(js)
        precalc.append(precalc_data)
    for precalc_dist_file in precalc_dist_files:
        precalc_dist_data = None
        if precalc_dist_file.endswith('.json'):
            with open(precalc_dist_file) as js:
                precalc_dist_data = json.load(js)
                precalc_dist.append(precalc_dist_data)
              
    points_of_interest = []
    for i in range (len(precalc)):
        points_of_interest.append([i, 0, precalc_dist[i][0], precalc[i][0][0]])
        for j in range(1, len(precalc[i])-1):
            if LSM_exp(precalc_dist[i][1:j+1], 30) < points_of_interest[-1][2]:
                points_of_interest.append([i, j, LSM_exp(precalc_dist[i][1:j+1], 30), precalc[i][j][0]])
    
    
    points_of_interest = sorted(points_of_interest, key = lambda POI: POI[2], reverse = True)
    stopping_frames_id = [0 for i in range(len(precalc))]
    sum_of_frames = len(precalc)
    sum_of_errors = 0
    for i in range(len(precalc)):
        sum_of_errors += precalc[i][0][0]
    
    x.append(sum_of_frames/len(precalc))
    y.append(sum_of_errors/len(precalc))
    for i in range(len(points_of_interest)):
        sum_of_frames -= (stopping_frames_id[points_of_interest[i][0]]+1)
        sum_of_errors -= precalc[points_of_interest[i][0]][stopping_frames_id[points_of_interest[i][0]]][0]
        stopping_frames_id[points_of_interest[i][0]] = points_of_interest[i][1]
        sum_of_frames += (points_of_interest[i][1]+1)
        sum_of_errors += points_of_interest[i][3]
        x.append(sum_of_frames/len(precalc))
        y.append(sum_of_errors/len(precalc))    
    return x, y

def roc_curve_SES_stoppers(method, dataset):
    precalc_dir = PRECALC_DIRECTORIES[dataset][method]
    precalc_dist_dir = PRECALC_DISTANCE_DIRECTORIES[dataset][method]
    SMOOTHING_COEFICIENT = 0.9
    x = []
    y = []
    
    precalc = []
    precalc_dist = []
    precalc_dist_files = [os.path.join(precalc_dist_dir, x) for x in os.listdir(precalc_dist_dir)]
    precalc_files = [os.path.join(precalc_dir, x) for x in os.listdir(precalc_dir)]
    for precalc_file in precalc_files:
        precalc_data = None
        with open(precalc_file) as js:
            precalc_data = json.load(js)
        precalc.append(precalc_data)
    for precalc_dist_file in precalc_dist_files:
        precalc_dist_data = None
        if precalc_dist_file.endswith('.json'):
            with open(precalc_dist_file) as js:
                precalc_dist_data = json.load(js)
                precalc_dist.append(precalc_dist_data)
              
    points_of_interest = []
    for i in range (len(precalc)):
        points_of_interest.append([i, 0, precalc_dist[i][0], precalc[i][0][0]])
        for j in range(1, len(precalc[i])-1):
            if SES(precalc_dist[i][0:j], SMOOTHING_COEFICIENT)[-1] < points_of_interest[-1][2]:
                points_of_interest.append([i, j, SES(precalc_dist[i][0:j], SMOOTHING_COEFICIENT)[-1], precalc[i][j][0]])
    
    
    points_of_interest = sorted(points_of_interest, key = lambda POI: POI[2], reverse = True)
    stopping_frames_id = [0 for i in range(len(precalc))]
    sum_of_frames = len(precalc)
    sum_of_errors = 0
    for i in range(len(precalc)):
        sum_of_errors += precalc[i][0][0]
    
    x.append(sum_of_frames/len(precalc))
    y.append(sum_of_errors/len(precalc))
    for i in range(len(points_of_interest)):
        sum_of_frames -= (stopping_frames_id[points_of_interest[i][0]]+1)
        sum_of_errors -= precalc[points_of_interest[i][0]][stopping_frames_id[points_of_interest[i][0]]][0]
        stopping_frames_id[points_of_interest[i][0]] = points_of_interest[i][1]
        sum_of_frames += (points_of_interest[i][1]+1)
        sum_of_errors += points_of_interest[i][3]
        x.append(sum_of_frames/len(precalc))
        y.append(sum_of_errors/len(precalc))    
    return x, y

def roc_curve_stoppers(method, dataset):
    precalc_dir = PRECALC_DIRECTORIES[dataset][method]
    precalc_dist_dir = PRECALC_DISTANCE_DIRECTORIES[dataset][method]
    
    x = []
    y = []
    
    precalc = []
    precalc_dist = []
    precalc_dist_files = [os.path.join(precalc_dist_dir, x) for x in os.listdir(precalc_dist_dir)]
    precalc_files = [os.path.join(precalc_dir, x) for x in os.listdir(precalc_dir)]
    for precalc_file in precalc_files:
        precalc_data = None
        with open(precalc_file) as js:
            precalc_data = json.load(js)
        precalc.append(precalc_data)
    for precalc_dist_file in precalc_dist_files:
        precalc_dist_data = None
        if precalc_dist_file.endswith('.json'):
            with open(precalc_dist_file) as js:
                precalc_dist_data = json.load(js)
                precalc_dist.append(precalc_dist_data)
              
    points_of_interest = []
    for i in range (len(precalc)):
        points_of_interest.append([i, 0, precalc_dist[i][0], precalc[i][0][0]])
        for j in range(1, len(precalc[i])):
            if precalc_dist[i][j] < points_of_interest[-1][2]:
                points_of_interest.append([i, j, precalc_dist[i][j], precalc[i][j][0]])
    
    
    points_of_interest = sorted(points_of_interest, key = lambda POI: POI[2], reverse = True)
    stopping_frames_id = [0 for i in range(len(precalc))]
    sum_of_frames = len(precalc)
    sum_of_errors = 0
    for i in range(len(precalc)):
        sum_of_errors += precalc[i][0][0]
    
    x.append(sum_of_frames/len(precalc))
    y.append(sum_of_errors/len(precalc))
    for i in range(len(points_of_interest)):
        sum_of_frames -= stopping_frames_id[points_of_interest[i][0]]
        sum_of_errors -= precalc[points_of_interest[i][0]][stopping_frames_id[points_of_interest[i][0]]][0]
        stopping_frames_id[points_of_interest[i][0]] = points_of_interest[i][1]
        sum_of_frames += points_of_interest[i][1]
        sum_of_errors += points_of_interest[i][3]
        x.append(sum_of_frames/len(precalc))
        y.append(sum_of_errors/len(precalc))    
    return x, y

def roc_curve_fixed_stoppers(method, dataset):
    precalc_dir = PRECALC_DIRECTORIES[dataset][method]
    precalc_dist_dir = PRECALC_DISTANCE_DIRECTORIES[dataset][method]
    
    x = []
    y = []
    
    precalc = []
    precalc_dist = []
    precalc_dist_files = [os.path.join(precalc_dist_dir, x) for x in os.listdir(precalc_dist_dir)]
    precalc_files = [os.path.join(precalc_dir, x) for x in os.listdir(precalc_dir)]
    for precalc_file in precalc_files:
        precalc_data = None
        with open(precalc_file) as js:
            precalc_data = json.load(js)
        precalc.append(precalc_data)
    for precalc_dist_file in precalc_dist_files:
        precalc_dist_data = None
        if precalc_dist_file.endswith('.json'):
            with open(precalc_dist_file) as js:
                precalc_dist_data = json.load(js)
                precalc_dist.append(precalc_dist_data)
                
    points_of_interest = []
    for i in range (len(precalc)):
        points_of_interest.append([i, 0, 1, precalc[i][0][0]])
        for j in range(1, len(precalc[i])):
            if 1/j < points_of_interest[-1][2]:
                points_of_interest.append([i, j, 1/j, precalc[i][j][0]])
    
    
    points_of_interest = sorted(points_of_interest, key = lambda POI: POI[2], reverse = True)
    stopping_frames_id = [0 for i in range(len(precalc))]
    sum_of_frames = len(precalc)
    sum_of_errors = 0
    for i in range(len(precalc)):
        sum_of_errors += precalc[i][0][0]
    
    x.append(sum_of_frames/len(precalc))
    y.append(sum_of_errors/len(precalc))
    for i in range(len(points_of_interest)):
        sum_of_frames -= stopping_frames_id[points_of_interest[i][0]]
        sum_of_errors -= precalc[points_of_interest[i][0]][stopping_frames_id[points_of_interest[i][0]]][0]
        stopping_frames_id[points_of_interest[i][0]] = points_of_interest[i][1]
        sum_of_frames += (points_of_interest[i][1]+1)
        sum_of_errors += points_of_interest[i][3]
        x.append(sum_of_frames/len(precalc))
        y.append(sum_of_errors/len(precalc))
        
    return x, y

def roc_curve_base_a_b(method, dataset):
    precalc_dir = PRECALC_DIRECTORIES[dataset][method]
    SMALL_DELTA = 0.1
    x = []
    y = []
    
    precalc = []
    precalc_files = [os.path.join(precalc_dir, x) for x in os.listdir(precalc_dir)]
    for precalc_file in precalc_files:
        precalc_data = None
        with open(precalc_file) as js:
            precalc_data = json.load(js)
        precalc.append(precalc_data)
        
    points_of_interest = []
    
    for i in range(len(precalc)):
        curr = [i, 0, (SMALL_DELTA + precalc[i][0][1]) / 2, precalc[i][0][0]]
        points_of_interest.append(curr)
        for j in range(1, len(precalc[i])):
            delta = (SMALL_DELTA + precalc[i][j][1]) / (j + 2)
            if delta < points_of_interest[-1][2]:
                points_of_interest.append([i, j, delta, precalc[i][j][0]])
        if points_of_interest[-1] == curr:
            points_of_interest.append(i, 29, (SMALL_DELTA + precalc[i][-1][1]) / 31, precalc[i][-1][0])
    
    points_of_interest = sorted(points_of_interest, key = lambda POI: POI[2], reverse = True)
    stopping_frames_id = [0 for i in range(len(precalc))]
    sum_of_frames = len(precalc)
    sum_of_errors = 0
    for i in range(len(precalc)):
        sum_of_errors += precalc[i][0][0]
    
    x.append(sum_of_frames/len(precalc))
    y.append(sum_of_errors/len(precalc))
    for i in range(len(points_of_interest)):
        sum_of_frames -= (stopping_frames_id[points_of_interest[i][0]]+1)
        sum_of_errors -= precalc[points_of_interest[i][0]][stopping_frames_id[points_of_interest[i][0]]][0]
        stopping_frames_id[points_of_interest[i][0]] = points_of_interest[i][1]
        sum_of_frames += (points_of_interest[i][1]+1)
        sum_of_errors += points_of_interest[i][3]
        x.append(sum_of_frames/len(precalc))
        y.append(sum_of_errors/len(precalc))
        
    return x, y    

for i_dataset, dataset in enumerate(EPPS_DATASETS):
    plt.subplot(100 + 10 * len(EPPS_DATASETS) + i_dataset + 1)
    plt.title(('%s) ' % chr(ord('a') + i_dataset)) + DATASET_LABELS[dataset])

    plt.gca().xaxis.set_minor_locator(MultipleLocator(0.5))
    plt.gca().xaxis.set_major_locator(MultipleLocator(2))

    PLOT_LINEWIDTH = { 'base': 2.0, 'summation': 2.0, 'treap': 2.5 }
    
    for method in METHODS:
        a, b = roc_curve_base_a_b(method, dataset)
        plt.plot(a, b, \
                 label = PLOT_LABEL[method], \
                 color = PLOT_COLOR[method], \
                 linestyle = PLOT_LINESTYLE[method], \
                 linewidth = PLOT_LINEWIDTH[method])   
        
    x, y = roc_curve_stoppers('summation', dataset)
    plt.plot(x, y, label = "roc test", c = 'r')
    a, b = roc_curve_fixed_stoppers('summation', dataset)
    plt.plot(a, b, label = "fixed stage", c = 'b')
    c, d = roc_curve_SES_stoppers('summation', dataset)
    plt.plot(c, d, label = "SES", c = 'g')
    #e, f = roc_curve_LSM_AR_stoppers('summation', dataset)
    #plt.plot(e, f, label = "LSM linear", c = 'y')
    #g, h = roc_curve_LSM_AR_stoppers('summation', dataset)
    #plt.plot(g, h, label = "LSM squared", c = 'c')
    
    plt.xlim([1, 20])
    plt.ylim(EPPS_YLIMITS[dataset])
    plt.grid()
    plt.legend()
    plt.xlabel(r'Mean number of frames')
    plt.ylabel('Mean error level')
    plt.gca().xaxis.set_major_formatter(FormatStrFormatter('%.2f'))

plt.savefig('epps_%s.pdf' % '_'.join(EPPS_DATASETS), dpi=1200, bbox_inches='tight', pad_inches=0)
plt.show()