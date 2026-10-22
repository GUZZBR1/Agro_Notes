<?php

declare(strict_types=1);

namespace Drupal\plan\Hook;

use Drupal\Core\Hook\Attribute\Hook;
use Drupal\Core\Render\Element;

/**
 * Theme hook implementations for plan.
 */
class ThemeHooks {

  /**
   * Implements hook_theme().
   */
  #[Hook('theme')]
  public function theme() {
    return [
      'plan' => [
        'render element' => 'elements',
        'initial preprocess' => static::class . '::preprocessPlan',
      ],
    ];
  }

  /**
   * Prepares variables for plan templates.
   *
   * Default template: plan.html.twig.
   *
   * @param array $variables
   *   An associative array containing:
   *   - elements: An associative array containing the plan information and any
   *     fields attached to the plan. Properties used:
   *     - #plan: A \Drupal\plan\Entity\Plan object. The plan entity.
   *   - attributes: HTML attributes for the containing element.
   */
  public function preprocessPlan(array &$variables) {
    $variables['plan'] = $variables['elements']['#plan'] ?? NULL;
    // Helpful $content variable for templates.
    foreach (Element::children($variables['elements']) as $key) {
      $variables['content'][$key] = $variables['elements'][$key];
    }
  }

  /**
   * Implements hook_theme_suggestions_HOOK().
   */
  #[Hook('theme_suggestions_plan')]
  public function themeSuggestionsPlan(array $variables) {
    $suggestions = [];
    $plan = $variables['elements']['#plan'];
    $sanitized_view_mode = strtr($variables['elements']['#view_mode'], '.', '_');
    $suggestions[] = 'plan__' . $sanitized_view_mode;
    $suggestions[] = 'plan__' . $plan->bundle();
    $suggestions[] = 'plan__' . $plan->bundle() . '__' . $sanitized_view_mode;
    $suggestions[] = 'plan__' . $plan->id();
    $suggestions[] = 'plan__' . $plan->id() . '__' . $sanitized_view_mode;
    return $suggestions;
  }

}
