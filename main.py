from math import sqrt
from queue import PriorityQueue
import pygame
pygame.init()
pygame.font.init()
from enum import Enum
from copy import copy

FPS = 60

WINDOW_WIDTH =  800
WINDOW_HEIGHT = 900

SQUARE_SIZE = 20

GUI_WIDTH = WINDOW_WIDTH
GUI_HEIGHT = 100

SETTINGS_WIDTH = WINDOW_WIDTH
SETTINGS_HEIGHT = 100

GRID_WIDTH = WINDOW_WIDTH
GRID_HEIGHT = WINDOW_HEIGHT - GUI_HEIGHT - SETTINGS_HEIGHT

BUTTON_FONT = pygame.font.SysFont('Comic Sans MS', 30)


class Color(Enum):
    WALL = (0, 0, 0)
    START = (0, 255, 0)
    STOP = (255, 0, 0)
    CONSIDERED = (120, 120, 120)
    FRONT = (0, 255, 255)
    PATH = (255, 255, 100)


class Field(Enum):
    EMPTY = 1
    WALL = 2
    START = 3
    STOP = 4
    CONSIDERED = 5
    FRONT = 6
    PATH = 7

class Board:
    def __init__(self, rows: int, cols: int):
        self._board: list[list[Field]] = [[Field.EMPTY for _ in range(cols)] for _ in range(rows)]
        self._rows = rows
        self._cols = cols
        self._start = None
        self._stop = None

    def is_valid(self, row, col):
        return (0 <= row < self._rows) and (0 <= col < self._cols)

    @property
    def rows(self):
        return self._rows

    @property
    def cols(self):
        return self._cols

    def __getitem__(self, rowcol):
        row, col = rowcol
        return self._board[row][col]
    
    def __setitem__(self, rowcol, value):
        row, col = rowcol
        if value in (Field.START, Field.STOP) or rowcol in (self.start, self.stop):
            raise ValueError("Cannot set/override start/stop")
        self._board[row][col] = value

    def set_start(self, row, col):
        self._start = (row, col)
        self._board[row][col] = Field.START

    def set_stop(self, row, col):
        self._stop = (row, col)
        self._board[row][col] = Field.STOP

    @property
    def start(self):
        return self._start

    @property
    def stop(self):
        return self._stop

    def neighbours(self, square: tuple):
        if self.is_valid(square[0]+1, square[1]):
            yield (square[0]+1, square[1])
        if self.is_valid(square[0]-1, square[1]):
            yield (square[0]-1, square[1])
        if self.is_valid(square[0], square[1]+1):
            yield (square[0], square[1]+1)
        if self.is_valid(square[0], square[1]-1):
            yield (square[0], square[1]-1)
    
class Surface:
    def __init__(self, width, height, x, y):
        self.width = width
        self.height = height
        self.x = x
        self.y = y

    def contains(self, x, y):
        return (self.x <= x <= self.x+self.width) and (self.y <= y <= self.y+self.height)

class NumberEdit(Surface):
    def __init__(self, width, height, x, y, default=1, bg=(0, 0, 0)):
        super().__init__(width, height, x, y)
        self._value = default
        self.background_color = bg
        self.text_area = None
        self.create_text_area()
        self.up_button = Button(3*self.width//4, self.height//2, self.x + self.width//4, self.y, (100, 100, 0), text="Up")
        self.down_button = Button(3*self.width//4, self.height//2, self.x + self.width//4, self.y + self.height//2, (100, 0, 100), text="Down")

    def create_text_area(self):
        self.text_area = BUTTON_FONT.render(str(self._value), False, (255, 255, 255))

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, val):
        self._value = val
        self.create_text_area()

    def handle_mouse_down(self, x, y):
        if self.down_button.contains(x, y):
            self.value = max(self._value-1, 1)
        elif self.up_button.contains(x, y):
            self.value = min(self._value+1, 9)
        self.create_text_area()

    def draw(self, window: pygame.Surface):
        pygame.draw.rect(window, self.background_color, (self.x, self.y, self.width, self.height))
        window.blit(self.text_area, (self.x + self.width//8 - self.text_area.get_width()//2, self.y + self.height//2 - self.text_area.get_height()//2))
        self.up_button.draw(window)
        self.down_button.draw(window)


class GridSurface(Surface):
    def __init__(self, width: int, height: int, x: int, y: int, square_size: int, board: Board):
        super().__init__(width, height, x, y)
        self.square_size = square_size
        if width % square_size != 0 or height % square_size != 0:
            raise ValueError("Width or height not divisable by square size")
        self.board = board
        self.operation = None

    def draw(self, window):
        self.draw_board(window)

    def draw_board(self, window: pygame.Surface):
        for row in range(self.board.rows):
            for col in range(self.board.cols):
                color = None
                if self.board[row, col] == Field.WALL:
                    color = Color.WALL
                elif self.board[row, col] == Field.START:
                    color = Color.START
                elif self.board[row, col] == Field.STOP:
                    color = Color.STOP
                elif self.board[row, col] == Field.PATH:
                    color = Color.PATH
                elif self.board[row, col] == Field.CONSIDERED:
                    color = Color.CONSIDERED
                elif self.board[row, col] == Field.FRONT:
                    color = Color.FRONT
                if color:
                    pygame.draw.rect(window, color.value, (
                        self.x + col*SQUARE_SIZE, self.y + row*SQUARE_SIZE,
                        SQUARE_SIZE, SQUARE_SIZE
                ))

    def get_row_col(self, x, y):
        return (y - self.y)//self.square_size, (x - self.x)//self.square_size

    def handle_mouse_down(self, x, y):
        row, col = self.get_row_col(x, y)
        self.fill_square(row, col)

    def fill_square(self, row, col):
        if self.board[row, col] == Field.EMPTY:
            if not self.operation or self.operation == 'wall':
                self.board[row, col] = Field.WALL
                self.operation = 'wall'
        elif self.board[row, col] == Field.WALL:
            if not self.operation or self.operation == 'empty':
                self.board[row, col] = Field.EMPTY
                self.operation = 'empty'

    def handle_mouse_up(self, x, y):
        self.operation = None

    def handle_mouse_move(self, x, y, down_x, down_y):
        row, col = self.get_row_col(max(self.x, min(x, self.x+self.width-1)), max(self.y, min(y, self.y+self.height-1)))
        self.fill_square(row, col)

class Button(Surface):
    def __init__(self, width, height, x, y, color, on_click=None, text=None):
        super().__init__(width, height, x, y)
        self.color = color
        self.on_click = on_click
        self.text_area = None
        if text:
            self.text_area = BUTTON_FONT.render(text, False, (0, 0, 0))

    def click(self):
        self.on_click()

    def draw(self, window: pygame.Surface):
        pygame.draw.rect(window, self.color, (self.x, self.y, self.width, self.height))
        if self.text_area:
            window.blit(self.text_area, (self.x+(self.width//2)-self.text_area.get_width()//2, self.y+(self.height//2)-self.text_area.get_height()//2))
       


class GUISurface(Surface):
    def __init__(self, width, height, x, y):
        super().__init__(width, height, x, y)
        self.start_callback = None
        self.clear_callback = None
        self.clear = Button(width//3, height//2, x+(self.width//12), y+height//4, (100, 100, 0), text="Clear")
        self.start = Button(width//3, height//2, x+7*width//12, y+height//4, (200, 0, 200), text="Start")

    def set_start_callback(self, callback):
        self.start_callback = callback
        self.start.on_click = callback

    def set_clear_callback(self, callback):
        self.clear_callback = callback
        self.clear.on_click = callback

    def draw(self, window: pygame.Surface):
        pygame.draw.rect(window, (0, 0, 255), (self.x, self.y, self.width, self.height))
        self.clear.draw(window)
        self.start.draw(window)

    def handle_mouse_down(self, x, y):
        if self.start.contains(x, y):
            self.start.on_click()
        elif self.clear.contains(x, y):
            self.clear.on_click()

class IPathFinder:
    def generate_steps(self, board: Board) -> tuple[list, dict]:
        ...

class Settings(Surface):

    def __init__(self, width: int, height: int, x, y):
        super().__init__(width, height, x, y)
        self.dist = NumberEdit(width//8, height//2, x+2*width//8, y+height//4)
        self.heur = NumberEdit(width//8, height//2, x+width-3*width//8, y+height//4)
        self.dist_label = BUTTON_FONT.render('Cost weight', False,          (100, 255, 0))
        self.heur_label = BUTTON_FONT.render('Distance left weight', False, (100, 255, 0))

    def draw(self, window: pygame.Surface):
        pygame.draw.rect(window, (0, 0, 255), (self.x, self.y, self.width, self.height))
        window.blit(self.dist_label, (self.dist.x, self.y))
        window.blit(self.heur_label, (self.heur.x, self.y))
        self.dist.draw(window)
        self.heur.draw(window)

    def handle_mouse_down(self, x, y):
        if self.dist.contains(x, y):
            self.dist.handle_mouse_down(x, y)
        elif self.heur.contains(x, y):
            self.heur.handle_mouse_down(x, y)

    def get_dist_heur(self):
        return self.dist.value, self.heur.value

class App:
    def __init__(self, path_finder: IPathFinder):
        self.window = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        pygame.display.set_caption('A* visualization')
        self.clock = pygame.time.Clock()
        self.board = Board(GRID_HEIGHT//SQUARE_SIZE, GRID_WIDTH//SQUARE_SIZE)
        self.board.set_start(self.board.rows//2, self.board.cols//4)
        self.board.set_stop(self.board.rows//2, 3*self.board.cols//4)
        self.gui = GUISurface(GUI_WIDTH, GUI_HEIGHT, 0, 0)
        self.grid = GridSurface(GRID_WIDTH, GRID_HEIGHT, 0, GUI_HEIGHT, SQUARE_SIZE, self.board)
        self.settings = Settings(SETTINGS_WIDTH, SETTINGS_HEIGHT, 0, GUI_HEIGHT + GRID_HEIGHT)
        self.gui.set_start_callback(self.find_path)
        self.gui.set_clear_callback(self.clear)
        self.running  = False
        self.mode = 'user'
        self.path_finder = path_finder
        self.steps = None
        self.path = None
        self.current_step = None
        self.current_path_step = None

    def clear(self):
        if self.mode == 'end':
            self.clear_path()
            self.mode = 'user'
        elif self.mode == 'user':
            self.clear_walls()

    def clear_walls(self):
        for row in range(self.board.rows):
            for col in range(self.board.cols):
                if self.board[row, col] == Field.WALL:
                    self.board[row, col] = Field.EMPTY

    def clear_path(self):
        for row in range(self.board.rows):
            for col in range(self.board.cols):
                if self.board[row, col] not in (Field.EMPTY, Field.WALL, Field.START, Field.STOP):
                    self.board[row, col] = Field.EMPTY

    def find_path(self):
        self.clear_path()
        self.mode = 'pathfinder'
        dist, heur = self.settings.get_dist_heur()
        results = self.path_finder.generate_steps(self.board, dist, heur)
        if results == None:
            self.mode = 'user'
            return
        self.steps, self.path = results
        self.current_path_step = self.path[self.board.stop]
        self.current_step = 0
        
    def run(self):
        self.running = True
        mouse_down = False
        mouse_down_pos = None
        while self.running:
            self.window.fill((255, 255, 255))
            for event in pygame.event.get():  
                if event.type == pygame.QUIT:
                    self.running = False
                if event.type == pygame.MOUSEBUTTONDOWN and self.mode in ('end', 'user'):
                    x, y = pygame.mouse.get_pos()
                    if self.gui.contains(x, y):
                        self.gui.handle_mouse_down(x, y)
                    if self.grid.contains(x, y):
                        if self.mode == 'end':
                            self.clear()
                        self.grid.handle_mouse_down(x, y)
                    if self.settings.contains(x, y):
                        self.settings.handle_mouse_down(x, y)
                    mouse_down = True
                    mouse_down_pos = (x, y)
                if mouse_down and event.type == pygame.MOUSEMOTION:
                    x, y = pygame.mouse.get_pos()
                    if self.grid.contains(*mouse_down_pos):
                        self.grid.handle_mouse_move(x, y, *mouse_down_pos)
                if event.type == pygame.MOUSEBUTTONUP:
                    x, y = pygame.mouse.get_pos()
                    self.grid.handle_mouse_up(x, y)
                    mouse_down = False
                    mouse_down_pos = None
            self.draw()
            self.clock.tick(FPS)
            pygame.display.update()

    def draw(self):
        if self.mode == 'pathfinder':
            self.draw_steps()
        self.gui.draw(self.window)
        self.grid.draw(self.window)
        self.settings.draw(self.window)
                
    def draw_steps(self):
        if self.current_step < len(self.steps):
            self.draw_step(self.steps[self.current_step])
            self.current_step += 1
        elif self.current_path_step != self.board.start:
            self.board[self.current_path_step] = Field.PATH
            self.current_path_step = self.path[self.current_path_step]
        else:
            self.mode = 'end'

    def draw_step(self, step):
        if step['add'] and step['add'] not in (self.board.start, self.board.stop):
            self.board[step['add']] = Field.FRONT
        if step['rm'] and step['rm'] not in (self.board.start, self.board.stop):
            self.board[step['rm']] = Field.CONSIDERED


class AStar(IPathFinder):
    def generate_steps(self, board: Board, dist, heur):
        COST_W, HEUR_W = dist, heur
        start = board.start
        stop = board.stop
        frontier = PriorityQueue()
        frontier.put((0, start))
        came_from = {}
        cost_so_far = {}
        cost_so_far[start] = 0
        found = False
        steps = [{'add': start, 'rm': None}]
        while not frontier.empty():
            square=frontier.get(False)
            square = square[1]
            step = {'rm': square}
            step_added = False
            if square == stop:
                found = True
                break
            for (row, col) in board.neighbours(square):
                if board[row, col] == Field.WALL:
                    continue
                if ((row, col) not in cost_so_far) or (cost_so_far[(row, col)] > (cost_so_far[square]+1)):
                    cost_so_far[(row, col)] = cost_so_far[square]+1
                    priority = COST_W*cost_so_far[(row, col)] + HEUR_W*self.heuristic((row, col), stop)
                    frontier.put((priority, (row, col)))
                    step['add'] = (row, col)
                    steps.append(copy(step))
                    step_added = True
                    came_from[(row, col)] = square
            if not step_added:
                step['add'] = None
                steps.append(step)
        if found:
            return steps, came_from
        return None


    def heuristic(self, start, stop):
        # return abs(stop[0]-start[0]) + abs(stop[1]-start[1])
        return sqrt(pow(stop[0]-start[0], 2) + pow(stop[1]-start[1], 2))

def main():
    app = App(path_finder=AStar())
    app.run()

if __name__ == '__main__':
    main()
