# **************************************************************************** #
#                                                                              #
#                                                         :::      ::::::::    #
#    Makefile                                           :+:      :+:    :+:    #
#                                                     +:+ +:+         +:+      #
#    By: afreitas <afreitas@student.42.fr>          +#+  +:+       +#+         #
#                                                 +#+#+#+#+#+   +#+            #
#    Created: 2024/01/15 10:00:00 by afreitas          #+#    #+#              #
#    Updated: 2024/01/15 10:00:00 by afreitas         ###   ########.fr        #
#                                                                              #
# **************************************************************************** #

NAME = cub3d

CC = cc
CFLAGS = -Wall -Wextra -Werror -g -DGL_SILENCE_DEPRECATION
LDFLAGS = -lm -framework OpenGL -framework GLUT

# Directories
SRCDIR = src
INCDIR = includes
OBJDIR = obj

# Source files
SRCFILES = main.c \
		   parser/parser.c \
		   rendering/render.c \
		   texture/texture.c \
		   movement/movement.c \
		   utils/utils.c \
		   utils/memory.c \
		   macos_mlx.c

SRCS = $(addprefix $(SRCDIR)/, $(SRCFILES))
OBJS = $(SRCS:$(SRCDIR)/%.c=$(OBJDIR)/%.o)

# Colors
GREEN = \033[0;32m
RED = \033[0;31m
RESET = \033[0m

all: $(NAME)

$(NAME): $(OBJS)
	@echo "$(GREEN)Linking $(NAME)...$(RESET)"
	@$(CC) $(OBJS) $(LDFLAGS) -o $(NAME)
	@echo "$(GREEN)$(NAME) created successfully!$(RESET)"

$(OBJDIR)/%.o: $(SRCDIR)/%.c
	@mkdir -p $(dir $@)
	@echo "Compiling $<..."
	@$(CC) $(CFLAGS) -I$(INCDIR) -c $< -o $@

clean:
	@echo "$(RED)Cleaning object files...$(RESET)"
	@rm -rf $(OBJDIR)

fclean: clean
	@echo "$(RED)Cleaning $(NAME)...$(RESET)"
	@rm -f $(NAME)

re: fclean all

.PHONY: all clean fclean re
