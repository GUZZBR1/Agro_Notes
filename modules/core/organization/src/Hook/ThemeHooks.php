<?php

declare(strict_types=1);

namespace Drupal\organization\Hook;

use Drupal\Core\Hook\Attribute\Hook;
use Drupal\Core\Render\Element;

/**
 * Theme hook implementations for organization.
 */
class ThemeHooks {

  /**
   * Implements hook_theme().
   */
  #[Hook('theme')]
  public function theme() {
    return [
      'organization' => [
        'render element' => 'elements',
        'initial preprocess' => static::class . '::preprocessOrganization',
      ],
    ];
  }

  /**
   * Prepares variables for organization templates.
   *
   * Default template: organization.html.twig.
   *
   * @param array $variables
   *   An associative array containing:
   *   - elements: An associative array containing the organization information
   *     and any fields attached to the organization. Properties used:
   *     - #organization: A \Drupal\organization\Entity\Organization object. The
   *       organization entity.
   *   - attributes: HTML attributes for the containing element.
   */
  public function preprocessOrganization(array &$variables) {
    $variables['organization'] = $variables['elements']['#organization'];
    // Helpful $content variable for templates.
    foreach (Element::children($variables['elements']) as $key) {
      $variables['content'][$key] = $variables['elements'][$key];
    }
  }

  /**
   * Implements hook_theme_suggestions_HOOK().
   */
  #[Hook('theme_suggestions_organization')]
  public function themeSuggestionsOrganization(array $variables) {
    $suggestions = [];
    $organization = $variables['elements']['#organization'];
    $sanitized_view_mode = strtr($variables['elements']['#view_mode'], '.', '_');
    $suggestions[] = 'organization__' . $sanitized_view_mode;
    $suggestions[] = 'organization__' . $organization->bundle();
    $suggestions[] = 'organization__' . $organization->bundle() . '__' . $sanitized_view_mode;
    $suggestions[] = 'organization__' . $organization->id();
    $suggestions[] = 'organization__' . $organization->id() . '__' . $sanitized_view_mode;
    return $suggestions;
  }

}
