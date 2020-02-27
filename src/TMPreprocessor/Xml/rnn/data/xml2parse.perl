#!/usr/bin/perl -w

use strict;

#( (NP (NP (NN resumption)) (PP (IN of) (NP (DT the) (NN session)))) )
#( (S (@S (@S (@S (S (NP (PRP I)) (VP (VB declare) (VP (@VP (VBD resumed) (NP (@NP (NP (DT the) (NN session)) (PP (IN of) (NP (@NP (DT the) (NNP European)) (NNP Parliament)))) (VP (VBN adjourned) (PP (IN on) (NP (NNP Friday) (CD 17)))))) (NP (NNP December) (CD 1999))))) (, ,)) (CC and)) (S (NP (PRP I)) (VP (MD would) (VP (VB like) (S (ADVP (RB once) (RB again)) (VP (TO to) (VP (@VP (VB wish) (NP (PRP you))) (NP (NP (@NP (@NP (DT a) (JJ happy)) (JJ new)) (NN year)) (PP (IN in) (NP (@NP (DT the) (NN hope)) (SBAR (IN that) (S (NP (PRP you)) (VP (VBD enjoyed) (NP (@NP (@NP (DT a) (JJ pleasant)) (JJ festive)) (NN period))))))))))))))) (. .)) )

while(<STDIN>) {
  if (/^$/) {
    print "\n"; # parse failures
    next;
  }


  # main
  s/<(T\d+)>/\($1/g;
  s/<\/T\d+>/\)/g;
  s/^/\(T /;
  s/$/\)/;

  # cleanup
  s/ +/ /g;
  s/ $//g;
  s/\)$/ \)/g;

  # output
  print $_;
}
