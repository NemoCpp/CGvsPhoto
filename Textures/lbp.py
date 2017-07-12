import numpy as np 
from CGvsPhoto import image_loader as il

from multiprocessing import Pool

from functools import partial

from sklearn.svm import SVC
from sklearn.metrics import accuracy_score

def compute_code(minipatch, mode = 'ltc'): 

	s = np.sign(minipatch - minipatch[1,1])
	# print(s)
	if mode == 'lbp':
		s[s == -1] = 0
		# print(s)
		binary = array_to_bin(s)
		# print(binary)

		return(binary)
	if mode == 'ltc': 
		return((str(int(np.sum(s[s==1])))+ 'u', str(-int(np.sum(s[s == -1]))) + 'l'))
	# return('0b100000000')

def get_classes(mode = 'ltc'):
	classes = dict()
	if mode == 'lbp':
		n = 0
		for i in range(511):
			b = '{:08b}'.format(i)
			A = [[int(b[0]), int(b[1]), int(b[2])], 
				 [int(b[7]), 0, int(b[3])],
				 [int(b[6]), int(b[5]), int(b[4])]]

			b = array_to_bin(np.array(A))
			if b not in classes:
				classes[b] = n
				n+=1 
		
	if mode == 'ltc': 
		n = 0
		for i in range(9):
			classes[str(i) + 'l'] = n
			classes[str(i) + 'u'] = n + 1
			n+=2

	print(str(n) + ' classes')
	return(classes)

def compute_error_image(image): 
	prediction = np.empty([image.shape[0] - 1, image.shape[1] - 1])
	for i in range(image.shape[0]-1):
		for j in range(image.shape[1]-1):
			a = image[i, j+1] 
			b = image[i+1, j]
			c = image[i+1, j+1]

			if c <= min(a,b):
				prediction[i,j] = max(a,b)
			else: 
				if c >= max(a,b):
					prediction[i,j] = min(a,b)
				else: 
					prediction[i,j] = a + b -c
	# print(prediction.shape)
	# print(image.shape)
	error = image[:image.shape[0]-1, :image.shape[1]-1, 0] - prediction 
	# print(error.shape)
	return(error)

def array_to_bin(A): 

	T = [int(A[0,0]), int(A[0,1]), int(A[0,2]), int(A[1,2]), int(A[2,2]),
	     int(A[2,1]), int(A[2,0]), int(A[1,0])]

	nb_c = 0
	for i in range(1,8): 
		if T[i-1] != T[i]: 
			nb_c += 1

	if nb_c > 2: 
		binary = '0b100000000'
	else: 
		binary = '0b' + str(T[0]) + str(T[1]) + str(T[2]) + str(T[3]) + str(T[4]) + str(T[5]) + str(T[6]) + str(T[7])

	return(binary)

def compute_hist(image, mode = 'ltc'): 

	hist_1 = dict()
	hist_2 = dict()
	# hist_error = dict()
	for i in classes.keys():
		hist_1[i] = 0
		hist_2[i] = 0
		# hist_error[i] = 0


	# error = compute_error_image(image)

	for i in range(1, image.shape[0] - 2): 
		for j in range(1, image.shape[1] - 2): 
			if mode == 'lbp':
				b = compute_code(image[i-1:i+2, j-1:j+2,0], mode)
				hist_1[b] += 1
				b = compute_code(image[i-1:i+2, j-1:j+2,1], mode)
				hist_2[b] += 1

			if mode == 'ltc':
				b = compute_code(image[i-1:i+2, j-1:j+2,0], mode)
				hist_1[b[0]] += 1
				hist_1[b[1]] += 1
				b = compute_code(image[i-1:i+2, j-1:j+2,1], mode)
				hist_2[b[0]] += 1
				hist_2[b[1]] += 1				
			# b_error = compute_code(error[i-1:i+2, j-1:j+2])
			# hist_error[b_error] += 1

	F = []
	N = (image.shape[0] - 3)*(image.shape[1] - 3)
	for i in hist_1.keys():
		F.append(hist_1[i]/N)
		F.append(hist_2[i]/N)
		# F.append(hist_error[i])

	return(np.array(F))


def compute_features(data, i, batch_size, nb_batch, mode = 'ltc'): 

	print('Compute features for batch ' + str(i+1) + '/' + str(nb_batch))
	images, labels = data[0], data[1]
	features = []
	y_train = []
	for i in range(batch_size): 
		features.append(compute_hist(images, mode))
		y_train.append(labels[0])

	print(features[0])
	return(features, y_train)

def compute_testing_features(i, batch_size, nb_test_batch, data): 

	print('Compute features for testing batch ' + str(i+1) + '/' + str(nb_test_batch))
	images, labels = data.get_batch_test(batch_size = batch_size,
											   crop = False)

	features = []
	y_test = []
	for i in range(batch_size): 
		features.append(compute_hist(images))
		y_test.append(labels[0])

	return(features, y_test)

if __name__ == '__main__': 

	data_directory = '/work/smg/v-nicolas/level-design_raise/'
	image_size = None

	data = il.Database_loader(directory = data_directory, 
							  size = image_size, only_green = False)

	mode = 'lbp'

	classes = get_classes(mode)

	nb_train_batch = 10
	batch_size = 1

	print('Training...')
	features_train = np.empty([nb_train_batch*batch_size, 2*len(classes.keys())])
	y_train = np.empty([nb_train_batch*batch_size,])

	data_train = []
	for i in range(nb_train_batch):
		print('Getting batch ' + str(i+1) + '/' + str(nb_train_batch))
		images_batch, y_batch = data.get_next_train(crop = False)
		data_train.append([images_batch, y_batch])

	pool = Pool()  

	to_compute = [i for i in range(nb_train_batch)]
	result = pool.starmap(partial(compute_features, 
							  batch_size = batch_size, 
							  nb_batch = nb_train_batch, 
							  mode = mode),
							  zip(data_train, to_compute)) 


	del(data_train)

	index = 0
	for i in range(len(result)):
		features_train[index:index+batch_size] = result[i][0]
		y_train[index:index+batch_size] = result[i][1]

		index+=batch_size


	del(result)

	clf = SVC()


	print('Fitting SVM...')

	clf.fit(features_train, y_train)


	print('Testing...')

	nb_test_batch = 500

	features_test = np.empty([nb_test_batch*batch_size, 2*len(classes.keys())])
	y_test = np.empty([nb_test_batch*batch_size,])



	data_test = []
	for i in range(nb_test_batch):
		print('Getting batch ' + str(i+1) + '/' + str(nb_test_batch))
		images_batch, y_batch = data.get_next_test(crop = False)
		data_test.append([images_batch, y_batch])
	pool = Pool()  

	to_compute = [i for i in range(nb_test_batch)]
	result = pool.starmap(partial(compute_features, 
							  batch_size = batch_size, 
							  nb_batch = nb_test_batch,
							  mode = mode),
							  zip(data_test, to_compute)) 

	del(data_test)
	index = 0
	for i in range(len(result)):
		features_test[index:index+batch_size] = result[i][0]
		y_test[index:index+batch_size] = result[i][1]

		index+=batch_size


	del(result)


	print('Prediction...')
	y_pred = clf.predict(features_test)

	score = accuracy_score(y_pred,y_test)

	print("Accuracy : " + str(score))


