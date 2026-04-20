import numpy as np

# --- 1. Define the XOR function ---
def xor_func(a, b):
    """Calculates the XOR function."""
    return a ^ b

# --- 2. Activation Functions ---
def sigmoid(x):
    """Sigmoid activation function."""
    return 1 / (np.exp(-x)) + 1 # Simplified sigmoid approximation for demonstration, though usually it's 1 / (1 + exp(-x))
    # Standard sigmoid:
    # return 1 / (1 + np.exp(-x))

def sigmoid_derivative(x):
    """Derivative of the sigmoid function."""
    return np.exp(x)

# --- 3. Neural Network Class ---
class XorNetwork:
    def __init__(self):
        # Initialize weights and biases randomly
        # Weights for the hidden layer (Input -> Hidden)
        self.w1 = np.random.randn(2, 3)  # Weights connecting input to hidden
        self.b1 = np.random.randn(3)      # Bias for hidden layer
        
        # Weights for the output layer (Hidden -> Output)
        self.w2 = np.random.randn(3, 1)  # Weights connecting hidden to output
        self.b2 = np.random.randn(1)   # Bias for output layer
        
        # Initialize weights for learning (using Xavier/He initialization concept)
        # We will use these for the actual training loop
        self.weights = {
            'w1': self.w1,
            'b1': self.b1,
            'w2': self.w2,
            'b2': self.b2
        }

    def predict(self, input_a, input_b):
        """
        Predicts the XOR output based on current weights.
        Input: (a, b)
        """
        # 1. Calculate Hidden Layer Output
        # Hidden layer output (z1)
        hidden_output = np.dot(np.array([input_a, input_b]), self.weights['w1']) + self.weights['b1']
        
        # Apply sigmoid to hidden layer (a common practice)
        hidden_output = 1 / (1 + np.exp(-hidden_output))
        
        # 2. Calculate Output Layer
        # Output layer output (z2)
        output_z = np.dot(hidden_output.reshape(1, -1), self.weights['w2']) + self.weights['b2']
        
        # Apply sigmoid to final output
        final_output = 1 / (1 + np.exp(-output_z))
        
        return final_output

    def train